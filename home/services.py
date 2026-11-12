from decimal import Decimal

from django.db import transaction
from django.db.models import F

from .constants import MAX_ITEM_QUANTITY, calculate_shipping
from .models import Order, OrderItem, Product, ProductVariant


class OrderError(Exception):
    """Raised when an order cannot be placed. The cart is left untouched."""


@transaction.atomic
def place_order(user, cart, address, notes=''):
    """Create a COD order from the cart using only trusted database values.

    Stock and prices are re-read inside the transaction, so manipulated
    requests cannot change what the customer is charged.
    """
    items = list(
        cart.items.select_related(
            'product', 'variant', 'variant__size', 'variant__color'
        ).select_for_update()
    )
    if not items:
        raise OrderError('Your cart is empty.')

    variant_ids = [item.variant_id for item in items if item.variant_id]
    product_ids = [item.product_id for item in items if item.product_id]
    locked_variants = {
        variant.pk: variant
        for variant in ProductVariant.objects.select_for_update()
        .filter(pk__in=variant_ids)
        .select_related('size', 'color')
    }
    locked_products = {
        product.pk: product
        for product in Product.objects.select_for_update().filter(pk__in=product_ids)
    }

    subtotal = Decimal('0.00')
    order_lines = []
    for item in items:
        product = locked_products.get(item.product_id)
        variant = locked_variants.get(item.variant_id)
        if product is None or variant is None:
            raise OrderError(
                'One of the products in your cart is no longer available.'
            )
        if not product.is_active:
            raise OrderError(f'{product.name} is no longer available.')
        if item.quantity < 1 or item.quantity > MAX_ITEM_QUANTITY:
            raise OrderError('Please review the quantity in your cart.')
        if variant.stock < item.quantity:
            raise OrderError(
                f'Sorry, only {variant.stock} unit(s) of {product.name} '
                f'({variant.size} / {variant.color}) are currently available.'
            )
        line_total = product.price * item.quantity
        subtotal += line_total
        image = product.primary_image
        order_lines.append(
            {
                'product': product,
                'variant': variant,
                'product_name': product.name,
                'size_name': variant.size.name,
                'color_name': variant.color.name,
                'image_url': image.url if image else '',
                'unit_price': product.price,
                'quantity': item.quantity,
                'subtotal': line_total,
            }
        )

    shipping_fee = calculate_shipping(subtotal)
    order = Order(
        user=user,
        status=Order.Status.PENDING,
        payment_method=Order.PaymentMethod.COD,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=subtotal + shipping_fee,
        full_name=address.full_name,
        phone=address.phone,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        city=address.city,
        state=address.state,
        postal_code=address.postal_code,
        country=address.country,
        notes=notes,
        stock_deducted=True,
    )
    order.save()

    OrderItem.objects.bulk_create(
        [OrderItem(order=order, **line) for line in order_lines]
    )

    for line in order_lines:
        ProductVariant.objects.filter(pk=line['variant'].pk).update(
            stock=F('stock') - line['quantity']
        )
        Product.objects.filter(pk=line['product'].pk).update(
            sold_count=F('sold_count') + line['quantity']
        )

    cart.items.all().delete()
    return order
