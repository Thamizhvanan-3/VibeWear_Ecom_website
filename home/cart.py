from django.db import transaction

from .models import Cart, CartItem


def get_cart(request, create=True):
    """Return the active cart for the current user or guest session."""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart is None and create:
            cart = Cart.objects.create(user=request.user)
        return cart

    cart_id = request.session.get('cart_id')
    if cart_id:
        cart = Cart.objects.filter(pk=cart_id, user__isnull=True).first()
        if cart is not None:
            return cart
        request.session.pop('cart_id', None)

    if not create:
        return None

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(user=None, session_key=session_key)
    request.session['cart_id'] = cart.pk
    return cart


def merge_guest_cart(request, user):
    """Merge the current guest cart into the user's saved cart after login."""
    guest_id = request.session.get('cart_id')
    guest_cart = None
    if guest_id:
        guest_cart = Cart.objects.filter(pk=guest_id, user__isnull=True).first()
    if guest_cart is None and request.session.session_key:
        guest_cart = Cart.objects.filter(
            user__isnull=True, session_key=request.session.session_key
        ).first()
    if guest_cart is None:
        return

    with transaction.atomic():
        user_cart, _ = Cart.objects.get_or_create(user=user)
        if user_cart.pk == guest_cart.pk:
            return

        guest_items = list(
            guest_cart.items.select_related('product', 'variant', 'variant__size')
        )
        for item in guest_items:
            if not item.product.is_active or item.variant.stock <= 0:
                continue
            quantity = min(item.quantity, item.variant.stock)
            existing = CartItem.objects.filter(
                cart=user_cart, variant=item.variant
            ).first()
            if existing:
                existing.quantity = min(
                    existing.quantity + quantity, item.variant.stock
                )
                existing.save(update_fields=['quantity'])
            else:
                CartItem.objects.create(
                    cart=user_cart,
                    product=item.product,
                    variant=item.variant,
                    quantity=quantity,
                )
        guest_cart.delete()

    request.session.pop('cart_id', None)


def cart_item_count(request):
    cart = get_cart(request, create=False)
    if cart is None:
        return 0
    return cart.total_quantity
