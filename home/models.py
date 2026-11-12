import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.db.models import F, Sum, Value
from django.db.models.functions import Greatest
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def unique_slug(instance, value, slug_field='slug', max_length=200):
    """Return a slug that is unique for the instance's model."""
    base = slugify(value)[:max_length] or 'item'
    slug = base
    model = instance.__class__
    counter = 2
    while model.objects.filter(**{slug_field: slug}).exclude(pk=instance.pk).exists():
        suffix = f'-{counter}'
        slug = f'{base[:max_length - len(suffix)]}{suffix}'
        counter += 1
    return slug


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    description = models.TextField(blank=True)
    image = models.FileField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        if self.parent_id:
            return f'{self.parent.name} / {self.name}'
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, max_length=140)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('shop')}?category={self.slug}"

    @property
    def is_subcategory(self):
        return self.parent_id is not None


class Size(models.Model):
    name = models.CharField(max_length=20, unique=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=40, unique=True)
    hex_code = models.CharField(
        max_length=7,
        default='#000000',
        help_text='Hex colour used in the storefront, for example #1a1a1a.',
        validators=[
            RegexValidator(
                regex=r'^#[0-9a-fA-F]{6}$',
                message='Enter a colour in #RRGGBB format.',
            )
        ],
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='products'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Optional MRP. Leave blank when the product is not discounted.',
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    sold_count = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, max_length=220)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.slug])

    @property
    def primary_image(self):
        images = list(self.images.all())
        return images[0] if images else None

    @property
    def all_images(self):
        return list(self.images.all())

    @property
    def total_stock(self):
        cached = getattr(self, '_prefetched_objects_cache', {}).get('variants')
        if cached is not None:
            return sum(variant.stock for variant in cached)
        return self.variants.aggregate(total=Sum('stock'))['total'] or 0

    @property
    def in_stock(self):
        return self.total_stock > 0

    @property
    def discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return int(
                ((self.original_price - self.price) / self.original_price) * 100
            )
        return 0

    @property
    def available_sizes(self):
        seen = []
        for variant in self.variants.all():
            if variant.size not in seen:
                seen.append(variant.size)
        return seen

    @property
    def available_colors(self):
        seen = []
        for variant in self.variants.all():
            if variant.color not in seen:
                seen.append(variant.color)
        return seen


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images'
    )
    image = models.FileField(upload_to='products/', blank=True, null=True)
    static_path = models.CharField(
        max_length=255,
        blank=True,
        help_text='Existing static image path such as home/image1.avif (optional).',
    )
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_primary', 'sort_order', 'id']

    def __str__(self):
        return self.alt_text or f'Image for {self.product.name}'

    @property
    def url(self):
        if self.image:
            return self.image.url
        if self.static_path:
            return static(self.static_path)
        return ''


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='variants'
    )
    size = models.ForeignKey(Size, on_delete=models.PROTECT, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name='variants')
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=64, unique=True, blank=True)

    class Meta:
        ordering = ['size__sort_order', 'color__name', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'size', 'color'],
                name='unique_product_size_color',
            )
        ]

    def __str__(self):
        return f'{self.product.name} - {self.size} / {self.color}'

    @property
    def in_stock(self):
        return self.stock > 0

    def save(self, *args, **kwargs):
        if not self.sku:
            base = slugify(
                f'{self.product.name}-{self.size.name}-{self.color.name}'
            ).upper()[:55]
            sku = base or 'VW-VARIANT'
            counter = 2
            while (
                ProductVariant.objects.filter(sku=sku)
                .exclude(pk=self.pk)
                .exists()
            ):
                suffix = f'-{counter}'
                sku = f'{base[:64 - len(suffix)]}{suffix}'
                counter += 1
            self.sku = sku
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9][0-9\s-]{6,18}$',
                message='Enter a valid phone number.',
            )
        ],
    )
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile - {self.user.username}'


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses'
    )
    label = models.CharField(
        max_length=40, blank=True, help_text='For example Home or Office.'
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9][0-9\s-]{6,18}$',
                message='Enter a valid phone number.',
            )
        ],
    )
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex=r'^[0-9A-Za-z -]{3,10}$',
                message='Enter a valid postal code.',
            )
        ],
    )
    country = models.CharField(max_length=100, default='India')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return f'{self.full_name}, {self.city}'

    def save(self, *args, **kwargs):
        if self.is_default and self.user_id:
            Address.objects.filter(user_id=self.user_id).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='wishlist_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'], name='unique_wishlist_product'
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.product.name}'


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(user__isnull=False),
                name='unique_cart_per_user',
            ),
            models.UniqueConstraint(
                fields=['session_key'],
                condition=models.Q(user__isnull=True),
                name='unique_guest_cart_session',
            ),
        ]

    def __str__(self):
        owner = self.user.username if self.user_id else f'Guest {self.session_key}'
        return f'Cart - {owner}'

    @property
    def total_quantity(self):
        cached = getattr(self, '_prefetched_objects_cache', {}).get('items')
        if cached is not None:
            return sum(item.quantity for item in cached)
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def subtotal(self):
        return sum((item.subtotal for item in self.items.all()), Decimal('0.00'))

    @property
    def shipping_fee(self):
        from .constants import calculate_shipping

        return calculate_shipping(self.subtotal)

    @property
    def total(self):
        return self.subtotal + self.shipping_fee


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['added_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'variant'], name='unique_cart_variant'
            )
        ]

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    @property
    def unit_price(self):
        return self.product.price

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        COD = 'cod', 'Cash on Delivery'

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')
    notes = models.TextField(blank=True)
    stock_deducted = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_order_number():
        while True:
            number = f'VW{timezone.now():%Y%m%d}{secrets.token_hex(3).upper()}'
            if not Order.objects.filter(order_number=number).exists():
                return number

    @property
    def can_cancel(self):
        return self.status in {self.Status.PENDING, self.Status.CONFIRMED}

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    def set_status(self, new_status):
        """Change status while keeping stock consistent.

        Cancelling a stock-deducted order returns the reserved units to
        inventory. Re-opening a cancelled order reserves them again only
        when enough stock is available.
        """
        new_status = str(new_status)
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if new_status == order.status:
                return

            if new_status == self.Status.CANCELLED and order.stock_deducted:
                for item in order.items.select_related('variant'):
                    if item.variant_id:
                        ProductVariant.objects.filter(pk=item.variant_id).update(
                            stock=F('stock') + item.quantity
                        )
                    if item.product_id:
                        Product.objects.filter(pk=item.product_id).update(
                            sold_count=Greatest(F('sold_count') - item.quantity, Value(0))
                        )
                order.stock_deducted = False
            elif order.status == self.Status.CANCELLED and not order.stock_deducted:
                items = list(order.items.select_related('variant'))
                for item in items:
                    if item.variant_id and (
                        item.variant is None or item.variant.stock < item.quantity
                    ):
                        raise ValidationError(
                            'Not enough stock to re-open this order.'
                        )
                for item in items:
                    if item.variant_id:
                        ProductVariant.objects.filter(pk=item.variant_id).update(
                            stock=F('stock') - item.quantity
                        )
                    if item.product_id:
                        Product.objects.filter(pk=item.product_id).update(
                            sold_count=F('sold_count') + item.quantity
                        )
                order.stock_deducted = True

            order.status = new_status
            order.save(update_fields=['status', 'stock_deducted', 'updated_at'])
            self.status = order.status
            self.stock_deducted = order.stock_deducted


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
    )
    product_name = models.CharField(max_length=200)
    size_name = models.CharField(max_length=20, blank=True)
    color_name = models.CharField(max_length=40, blank=True)
    image_url = models.CharField(max_length=300, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.product_name} x {self.quantity}'
