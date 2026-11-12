from django.contrib import admin, messages
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils.html import format_html

from .constants import LOW_STOCK_THRESHOLD
from .models import (
    Address,
    Cart,
    CartItem,
    Category,
    Color,
    Order,
    OrderItem,
    Product,
    ProductImage,
    ProductVariant,
    Size,
    UserProfile,
    Wishlist,
)


def stock_total_subquery():
    totals = (
        ProductVariant.objects.filter(product=OuterRef('pk'))
        .order_by()
        .values('product')
        .annotate(total=Sum('stock'))
        .values('total')[:1]
    )
    return Coalesce(Subquery(totals, output_field=IntegerField()), 0)


class LowStockFilter(admin.SimpleListFilter):
    title = 'stock level'
    parameter_name = 'stock_level'

    def lookups(self, request, model_admin):
        return (
            ('low', f'Low stock (<= {LOW_STOCK_THRESHOLD})'),
            ('out', 'Out of stock'),
            ('in', 'In stock'),
        )

    def queryset(self, request, queryset):
        queryset = queryset.annotate(_low_stock_total=stock_total_subquery())
        if self.value() == 'low':
            return queryset.filter(
                _low_stock_total__gt=0, _low_stock_total__lte=LOW_STOCK_THRESHOLD
            )
        if self.value() == 'out':
            return queryset.filter(_low_stock_total=0)
        if self.value() == 'in':
            return queryset.filter(_low_stock_total__gt=0)
        return queryset


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'static_path', 'alt_text', 'is_primary', 'sort_order', 'preview')
    readonly_fields = ('preview',)

    @admin.display(description='Preview')
    def preview(self, obj):
        if obj and obj.url:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px;" alt="">',
                obj.url,
            )
        return '—'


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color', 'stock', 'sku')
    autocomplete_fields = ('size', 'color')


class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'thumbnail',
        'name',
        'category',
        'price',
        'stock_status',
        'sold_count',
        'is_featured',
        'is_new_arrival',
        'is_active',
    )
    list_display_links = ('thumbnail', 'name')
    list_editable = ('price', 'is_featured', 'is_new_arrival', 'is_active')
    list_filter = (
        LowStockFilter,
        'is_active',
        'is_featured',
        'is_new_arrival',
        'category',
        'variants__size',
        'variants__color',
    )
    search_fields = ('name', 'description', 'category__name', 'variants__sku')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('sold_count', 'created_at', 'updated_at', 'large_preview')
    inlines = (ProductImageInline, ProductVariantInline)
    list_per_page = 25
    actions = (
        'mark_featured',
        'unmark_featured',
        'activate_products',
        'deactivate_products',
    )
    fieldsets = (
        (
            'Product',
            {
                'fields': (
                    'name',
                    'slug',
                    'category',
                    'description',
                    'price',
                    'original_price',
                )
            },
        ),
        (
            'Merchandising',
            {
                'fields': (
                    'is_active',
                    'is_featured',
                    'is_new_arrival',
                    'sold_count',
                    'created_at',
                    'updated_at',
                    'large_preview',
                )
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('category')
            .prefetch_related('images')
            .annotate(_stock_total=stock_total_subquery())
        )

    @admin.display(description='Image')
    def thumbnail(self, obj):
        image = obj.primary_image
        if image and image.url:
            return format_html(
                '<img src="{}" style="height:48px;width:48px;object-fit:cover;'
                'border-radius:6px;" alt="">',
                image.url,
            )
        return '—'

    @admin.display(description='Preview')
    def large_preview(self, obj):
        image = obj.primary_image if obj and obj.pk else None
        if image and image.url:
            return format_html(
                '<img src="{}" style="max-height:220px;border-radius:8px;" alt="">',
                image.url,
            )
        return 'No image yet.'

    @admin.display(description='Stock', ordering='_stock_total')
    def stock_status(self, obj):
        total = getattr(obj, '_stock_total', 0) or 0
        if total == 0:
            return format_html(
                '<strong style="color:#b31414;">Out of stock</strong>'
            )
        if total <= LOW_STOCK_THRESHOLD:
            return format_html(
                '<strong style="color:#b36b00;">Low: {} left</strong>', total
            )
        return format_html('<span style="color:#1b7f3b;">{} in stock</span>', total)

    @admin.action(description='Mark selected products as featured')
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} product(s) marked featured.', messages.SUCCESS)

    @admin.action(description='Remove featured flag from selected products')
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} product(s) updated.', messages.SUCCESS)

    @admin.action(description='Activate selected products')
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} product(s) activated.', messages.SUCCESS)

    @admin.action(description='Deactivate selected products')
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} product(s) deactivated.', messages.SUCCESS)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug', 'product_count', 'is_active')
    list_filter = ('is_active', 'parent')
    list_editable = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)

    @admin.display(description='Products')
    def product_count(self, obj):
        return obj.products.count()


class SizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'variant_count')
    list_editable = ('sort_order',)
    search_fields = ('name',)
    ordering = ('sort_order', 'name')

    @admin.display(description='Variants')
    def variant_count(self, obj):
        return obj.variants.count()


class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'swatch', 'hex_code', 'variant_count')
    search_fields = ('name',)

    @admin.display(description='Swatch')
    def swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:18px;height:18px;'
            'border-radius:50%;border:1px solid #999;background:{};"></span>',
            obj.hex_code,
        )

    @admin.display(description='Variants')
    def variant_count(self, obj):
        return obj.variants.count()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ('phone', 'date_of_birth')


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = (
        'label',
        'full_name',
        'phone',
        'city',
        'state',
        'postal_code',
        'is_default',
    )


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, AddressInline)
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'order_count',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'orders__order_number')
    ordering = ('-date_joined',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_order_count=Count('orders'))

    @admin.display(description='Orders', ordering='_order_count')
    def order_count(self, obj):
        return getattr(obj, '_order_count', 0)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = (
        'product_name',
        'size_name',
        'color_name',
        'unit_price',
        'quantity',
        'subtotal',
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'status',
        'payment_method',
        'item_count',
        'total',
        'stock_deducted',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = (
        'order_number',
        'user__username',
        'user__email',
        'full_name',
        'phone',
    )
    date_hierarchy = 'created_at'
    list_select_related = ('user',)
    inlines = (OrderItemInline,)
    readonly_fields = (
        'order_number',
        'user',
        'subtotal',
        'shipping_fee',
        'total',
        'stock_deducted',
        'full_name',
        'phone',
        'address_line1',
        'address_line2',
        'city',
        'state',
        'postal_code',
        'country',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (
            'Order',
            {
                'fields': (
                    'order_number',
                    'user',
                    'status',
                    'payment_method',
                    'created_at',
                    'updated_at',
                )
            },
        ),
        (
            'Delivery address',
            {
                'fields': (
                    'full_name',
                    'phone',
                    'address_line1',
                    'address_line2',
                    'city',
                    'state',
                    'postal_code',
                    'country',
                )
            },
        ),
        (
            'Totals',
            {'fields': ('subtotal', 'shipping_fee', 'total', 'stock_deducted')},
        ),
        ('Notes', {'fields': ('notes',)}),
    )
    actions = (
        'mark_confirmed',
        'mark_processing',
        'mark_shipped',
        'mark_delivered',
        'mark_cancelled',
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Items')
    def item_count(self, obj):
        return obj.items.count()

    def save_model(self, request, obj, form, change):
        if change:
            old_status = (
                Order.objects.filter(pk=obj.pk)
                .values_list('status', flat=True)
                .first()
            )
            new_status = obj.status
            if old_status and old_status != new_status:
                obj.status = old_status
                super().save_model(request, obj, form, change)
                try:
                    obj.set_status(new_status)
                except Exception as exc:  # pragma: no cover - admin feedback
                    self.message_user(
                        request,
                        f'Status could not be changed: {exc}',
                        messages.ERROR,
                    )
                return
        super().save_model(request, obj, form, change)

    def _set_status(self, request, queryset, status):
        updated = 0
        for order in queryset:
            if order.status != status:
                try:
                    order.set_status(status)
                    updated += 1
                except Exception as exc:  # pragma: no cover - admin feedback
                    self.message_user(
                        request,
                        f'{order.order_number}: {exc}',
                        messages.ERROR,
                    )
        self.message_user(
            request,
            f'{updated} order(s) marked as {dict(Order.Status.choices)[status]}.',
            messages.SUCCESS,
        )

    @admin.action(description='Mark selected orders as Confirmed')
    def mark_confirmed(self, request, queryset):
        self._set_status(request, queryset, Order.Status.CONFIRMED)

    @admin.action(description='Mark selected orders as Processing')
    def mark_processing(self, request, queryset):
        self._set_status(request, queryset, Order.Status.PROCESSING)

    @admin.action(description='Mark selected orders as Shipped')
    def mark_shipped(self, request, queryset):
        self._set_status(request, queryset, Order.Status.SHIPPED)

    @admin.action(description='Mark selected orders as Delivered')
    def mark_delivered(self, request, queryset):
        self._set_status(request, queryset, Order.Status.DELIVERED)

    @admin.action(description='Cancel selected orders and restore stock')
    def mark_cancelled(self, request, queryset):
        self._set_status(request, queryset, Order.Status.CANCELLED)


class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'user',
        'city',
        'state',
        'postal_code',
        'phone',
        'is_default',
    )
    list_filter = ('is_default', 'state', 'country')
    search_fields = ('full_name', 'user__username', 'user__email', 'phone', 'city')
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)


class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'product__name')
    autocomplete_fields = ('user', 'product')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    can_delete = False
    fields = ('product', 'variant', 'quantity', 'added_at')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class CartAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'session_key', 'item_count', 'updated_at')
    search_fields = ('user__username', 'user__email', 'session_key')
    readonly_fields = ('user', 'session_key', 'created_at', 'updated_at')
    inlines = (CartItemInline,)
    list_select_related = ('user',)

    @admin.display(description='Items')
    def item_count(self, obj):
        return obj.items.count()

    def has_add_permission(self, request):
        return False


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'date_of_birth', 'updated_at')
    search_fields = ('user__username', 'user__email', 'phone')
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')


try:
    admin.site.unregister(User)
except NotRegistered:  # pragma: no cover
    pass

admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Size, SizeAdmin)
admin.site.register(Color, ColorAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Cart, CartAdmin)

admin.site.site_header = 'VibeWear Administration'
admin.site.site_title = 'VibeWear Admin'
admin.site.index_title = 'Store overview'
