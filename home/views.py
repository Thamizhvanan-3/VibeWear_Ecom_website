from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import get_cart, merge_guest_cart
from .constants import MAX_ITEM_QUANTITY
from .forms import (
    AddressForm,
    CheckoutNotesForm,
    ContactForm,
    LoginForm,
    ProfileForm,
    RegistrationForm,
    StyledPasswordChangeForm,
)
from .models import (
    Address,
    CartItem,
    Category,
    Color,
    Order,
    Product,
    ProductVariant,
    Size,
    UserProfile,
    Wishlist,
)
from .services import OrderError, place_order


def _prefetch_catalog():
    return [
        'images',
        Prefetch(
            'variants',
            queryset=ProductVariant.objects.select_related('size', 'color'),
        ),
    ]


def _safe_next(request, default):
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default


def _cart_item_or_404(request, item_id):
    cart = get_cart(request, create=False)
    if cart is None:
        raise Http404('Cart not found')
    return get_object_or_404(CartItem, pk=item_id, cart=cart)


def _add_variant(cart, product, variant, quantity):
    """Add a variant to a cart and return (added, message, level)."""
    quantity = max(1, min(quantity, MAX_ITEM_QUANTITY))
    if variant.product_id != product.pk:
        return 0, 'That size and colour is not available for this product.', messages.ERROR
    if quantity > variant.stock:
        quantity = variant.stock
    if quantity <= 0:
        return 0, 'This size and colour is currently out of stock.', messages.ERROR

    item = CartItem.objects.filter(cart=cart, variant=variant).first()
    if item:
        new_quantity = min(item.quantity + quantity, variant.stock, MAX_ITEM_QUANTITY)
        added = max(0, new_quantity - item.quantity)
        if added == 0:
            return (
                0,
                'You already have the maximum available quantity in your cart.',
                messages.WARNING,
            )
        item.quantity = new_quantity
        item.save(update_fields=['quantity'])
    else:
        CartItem.objects.create(
            cart=cart, product=product, variant=variant, quantity=quantity
        )
        added = quantity

    if added < quantity:
        return (
            added,
            f'Only {added} more unit(s) could be added because of stock limits.',
            messages.WARNING,
        )
    return added, f'Added {product.name} to your cart.', messages.SUCCESS


def home(request):
    products = (
        Product.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related(*_prefetch_catalog())
        .order_by('-is_featured', '-created_at', '-id')
    )
    paginator = Paginator(products, 6)
    page_obj = paginator.get_page(request.GET.get('page'))

    new_arrivals = (
        Product.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related(*_prefetch_catalog())
        .order_by('-created_at', '-id')[:4]
    )
    best_sellers = (
        Product.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related(*_prefetch_catalog())
        .order_by('-sold_count', '-created_at')[:4]
    )
    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .annotate(
            product_count=Count(
                'products', filter=Q(products__is_active=True), distinct=True
            )
        )
        .prefetch_related('children')
    )
    return render(
        request,
        'home/home.html',
        {
            'page_obj': page_obj,
            'new_arrivals': new_arrivals,
            'best_sellers': best_sellers,
            'categories': categories,
        },
    )


def about(request):
    return render(request, 'home/about.html')


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        send_mail(
            subject=f'Message from {data["name"]}',
            message=data['message'],
            from_email=data['email'],
            recipient_list=['admin@vibewear.com'],
            fail_silently=True,
        )
        messages.success(
            request, "Thank you for contacting us! We'll get back to you soon."
        )
        return redirect('contact')
    return render(request, 'home/contact.html', {'form': form})


def contact_submit(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            send_mail(
                subject=f'Message from {data["name"]}',
                message=data['message'],
                from_email=data['email'],
                recipient_list=['admin@vibewear.com'],
                fail_silently=True,
            )
            messages.success(
                request, "Thank you for contacting us! We'll get back to you soon."
            )
            return redirect('contact')
        messages.error(request, 'Please check the contact form and try again.')
        return render(request, 'home/contact.html', {'form': form})
    return HttpResponse('Invalid request.')


def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='home.backends.EmailOrUsernameBackend')
        merge_guest_cart(request, user)
        messages.success(request, f'Welcome to VibeWear, {user.username}!')
        return redirect(_safe_next(request, 'home'))
    return render(request, 'home/signup.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user, backend='home.backends.EmailOrUsernameBackend')
        merge_guest_cart(request, user)
        messages.success(request, f'Welcome back, {user.username}!')
        return redirect(_safe_next(request, 'home'))
    return render(request, 'home/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


def shop(request):
    products = (
        Product.objects.filter(is_active=True)
        .select_related('category', 'category__parent')
        .prefetch_related(*_prefetch_catalog())
    )

    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    size_name = request.GET.get('size', '').strip()
    color_name = request.GET.get('color', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    sort = request.GET.get('sort', 'newest').strip()
    selected_category = None

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(category__parent__name__icontains=query)
        )
    if category_slug:
        selected_category = Category.objects.filter(
            slug=category_slug, is_active=True
        ).first()
        if selected_category:
            category_ids = [selected_category.pk]
            category_ids += list(
                selected_category.children.filter(is_active=True).values_list(
                    'pk', flat=True
                )
            )
            products = products.filter(category_id__in=category_ids)
    if size_name:
        products = products.filter(variants__size__name__iexact=size_name)
    if color_name:
        products = products.filter(variants__color__name__iexact=color_name)
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except (InvalidOperation, ValueError):
            min_price = ''
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except (InvalidOperation, ValueError):
            max_price = ''

    products = products.distinct()

    sort_options = {
        'newest': ('-created_at', '-id'),
        'price_asc': ('price', 'id'),
        'price_desc': ('-price', '-id'),
        'popular': ('-sold_count', '-created_at'),
        'name': ('name', 'id'),
    }
    if sort not in sort_options:
        sort = 'newest'
    products = products.order_by(*sort_options[sort])

    total_results = products.count()
    paginator = Paginator(products, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)
    base_query = params.urlencode()

    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related(
            Prefetch(
                'children',
                queryset=Category.objects.filter(is_active=True).order_by('name'),
            )
        )
        .order_by('name')
    )
    active_filter_count = sum(
        1
        for value in (query, category_slug, size_name, color_name, min_price, max_price)
        if value
    )

    return render(
        request,
        'home/shop.html',
        {
            'page_obj': page_obj,
            'categories': categories,
            'sizes': Size.objects.all(),
            'colors': Color.objects.all(),
            'selected_category': selected_category,
            'query': query,
            'category_slug': category_slug,
            'size_name': size_name,
            'color_name': color_name,
            'min_price': min_price,
            'max_price': max_price,
            'sort': sort,
            'base_query': base_query,
            'total_results': total_results,
            'active_filter_count': active_filter_count,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category', 'category__parent').prefetch_related(
            *_prefetch_catalog()
        ),
        slug=slug,
        is_active=True,
    )
    variants = list(product.variants.all())
    variant_data = [
        {
            'id': variant.pk,
            'size': variant.size.name,
            'color': variant.color.name,
            'hex': variant.color.hex_code,
            'stock': variant.stock,
        }
        for variant in variants
    ]
    related_products = (
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(pk=product.pk)
        .select_related('category')
        .prefetch_related(*_prefetch_catalog())
        .order_by('-sold_count', '-created_at')[:4]
    )
    if not related_products:
        related_products = (
            Product.objects.filter(is_active=True)
            .exclude(pk=product.pk)
            .select_related('category')
            .prefetch_related(*_prefetch_catalog())
            .order_by('-sold_count', '-created_at')[:4]
        )
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user, product=product
        ).exists()
    return render(
        request,
        'home/product_detail.html',
        {
            'product': product,
            'variants': variants,
            'variant_data': variant_data,
            'related_products': related_products,
            'in_wishlist': in_wishlist,
        },
    )


@require_POST
def add_to_cart(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related('images'), slug=slug, is_active=True
    )
    variant_id = request.POST.get('variant_id')
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    variant = ProductVariant.objects.filter(
        pk=variant_id, product=product
    ).select_related('size', 'color').first()
    if variant is None:
        messages.error(request, 'Please select a size and colour.')
        return redirect(product.get_absolute_url())

    cart = get_cart(request)
    added, message, level = _add_variant(cart, product, variant, quantity)
    messages.add_message(request, level, message)
    if added:
        return redirect(_safe_next(request, product.get_absolute_url()))
    return redirect(product.get_absolute_url())


@require_POST
def update_cart_item(request, item_id):
    item = _cart_item_or_404(request, item_id)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity <= 0:
        item.delete()
        messages.success(request, 'Item removed from your cart.')
        return redirect('cart')

    max_quantity = min(item.variant.stock, MAX_ITEM_QUANTITY)
    if max_quantity <= 0:
        item.delete()
        messages.warning(request, 'That item is out of stock and was removed.')
        return redirect('cart')
    if quantity > max_quantity:
        quantity = max_quantity
        messages.warning(
            request,
            f'Only {max_quantity} unit(s) are available for {item.product.name}.',
        )
    item.quantity = quantity
    item.save(update_fields=['quantity'])
    messages.success(request, 'Cart updated.')
    return redirect('cart')


@require_POST
def remove_cart_item(request, item_id):
    item = _cart_item_or_404(request, item_id)
    item.delete()
    messages.success(request, 'Item removed from your cart.')
    return redirect('cart')


def cart_detail(request):
    cart = get_cart(request)
    items = (
        cart.items.select_related(
            'product', 'variant', 'variant__size', 'variant__color'
        ).prefetch_related('product__images')
        if cart
        else []
    )
    return render(
        request,
        'home/cart.html',
        {
            'cart': cart,
            'items': items,
            'subtotal': cart.subtotal if cart else Decimal('0.00'),
            'shipping_fee': cart.shipping_fee if cart else Decimal('0.00'),
            'total': cart.total if cart else Decimal('0.00'),
        },
    )


@login_required
def wishlist(request):
    items = (
        Wishlist.objects.filter(user=request.user)
        .select_related('product', 'product__category')
        .prefetch_related(
            'product__images',
            Prefetch(
                'product__variants',
                queryset=ProductVariant.objects.select_related('size', 'color'),
            ),
        )
    )
    return render(request, 'home/wishlist.html', {'wishlist_items': items})


@require_POST
@login_required
def add_to_wishlist(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    _, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f'{product.name} added to your wishlist.')
    else:
        messages.info(request, f'{product.name} is already in your wishlist.')
    return redirect(_safe_next(request, product.get_absolute_url()))


@require_POST
@login_required
def remove_from_wishlist(request, slug):
    product = get_object_or_404(Product, slug=slug)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f'{product.name} removed from your wishlist.')
    return redirect(_safe_next(request, 'wishlist'))


@require_POST
@login_required
def move_wishlist_to_cart(request, item_id):
    wish = get_object_or_404(
        Wishlist.objects.select_related('product'), pk=item_id, user=request.user
    )
    variants = wish.product.variants.select_related('size', 'color')
    variant_id = request.POST.get('variant_id')
    variant = variants.filter(pk=variant_id).first() if variant_id else None
    if variant is None:
        variant = variants.filter(stock__gt=0).first()
    if variant is None:
        messages.error(request, f'{wish.product.name} is currently out of stock.')
        return redirect('wishlist')

    cart = get_cart(request)
    added, message, level = _add_variant(cart, wish.product, variant, 1)
    messages.add_message(request, level, message)
    if added:
        wish.delete()
    return redirect('cart' if added else 'wishlist')


@login_required
def checkout(request):
    cart = get_cart(request)
    items = (
        cart.items.select_related(
            'product', 'variant', 'variant__size', 'variant__color'
        ).prefetch_related('product__images')
        if cart
        else []
    )
    if not items:
        messages.info(request, 'Your cart is empty. Add something you love first.')
        return redirect('cart')

    addresses = Address.objects.filter(user=request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    default_name = request.user.get_full_name() or request.user.username
    address_form = AddressForm(
        initial={
            'full_name': default_name,
            'phone': profile.phone,
            'country': 'India',
            'is_default': not addresses.exists(),
        }
    )
    notes_form = CheckoutNotesForm()
    selected_address_id = request.POST.get('address_id') or request.GET.get('address')

    if request.method == 'POST':
        notes_form = CheckoutNotesForm(request.POST)
        address = None
        use_new_address = not selected_address_id or selected_address_id == 'new'

        if selected_address_id and selected_address_id != 'new':
            address = Address.objects.filter(
                pk=selected_address_id, user=request.user
            ).first()
            if address is None:
                messages.error(request, 'Please choose a valid delivery address.')

        if use_new_address:
            address_form = AddressForm(request.POST)
            if address_form.is_valid() and notes_form.is_valid():
                address = address_form.save(commit=False)
                address.user = request.user
                if not request.user.addresses.exists():
                    address.is_default = True
                address.save()
            else:
                messages.error(request, 'Please correct the delivery address details.')
        elif not notes_form.is_valid():
            messages.error(request, 'Please check the delivery instructions.')

        if address is not None and notes_form.is_valid():
            try:
                order = place_order(
                    request.user, cart, address, notes_form.cleaned_data['notes']
                )
            except OrderError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    f'Order {order.order_number} placed successfully. '
                    'Pay by cash when it arrives.',
                )
                return redirect(
                    f"{reverse('order_detail', args=[order.order_number])}?placed=1"
                )

    return render(
        request,
        'home/checkout.html',
        {
            'cart': cart,
            'items': items,
            'addresses': addresses,
            'address_form': address_form,
            'notes_form': notes_form,
            'selected_address_id': str(selected_address_id or ''),
            'subtotal': cart.subtotal,
            'shipping_fee': cart.shipping_fee,
            'total': cart.total,
        },
    )


def _get_customer_order(request, order_number):
    queryset = Order.objects.select_related('user').prefetch_related(
        'items__product', 'items__variant'
    )
    if request.user.is_staff:
        return get_object_or_404(queryset, order_number=order_number)
    return get_object_or_404(queryset, order_number=order_number, user=request.user)


@login_required
def order_detail(request, order_number):
    order = _get_customer_order(request, order_number)
    steps = [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
    ]
    timeline = []
    if order.status != Order.Status.CANCELLED:
        current_index = next(
            (index for index, step in enumerate(steps) if step.value == order.status),
            0,
        )
        timeline = [
            {
                'value': step.value,
                'label': step.label,
                'done': index <= current_index,
                'current': index == current_index,
            }
            for index, step in enumerate(steps)
        ]
    return render(
        request,
        'home/order_detail.html',
        {
            'order': order,
            'just_placed': request.GET.get('placed') == '1',
            'status_steps': steps,
            'timeline': timeline,
        },
    )


@login_required
def order_history(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related('items')
        .order_by('-created_at')
    )
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'home/orders.html', {'page_obj': page_obj})


@require_POST
@login_required
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status == Order.Status.CANCELLED:
        messages.info(request, 'This order is already cancelled.')
    elif not order.can_cancel:
        messages.error(
            request,
            'This order can no longer be cancelled. Please contact support.',
        )
    else:
        try:
            order.set_status(Order.Status.CANCELLED)
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
        else:
            messages.success(
                request, f'Order {order.order_number} has been cancelled.'
            )
    return redirect('order_detail', order_number=order.order_number)


@login_required
def dashboard(request):
    orders = Order.objects.filter(user=request.user)
    stats = {
        'orders': orders.count(),
        'pending': orders.filter(
            status__in=[
                Order.Status.PENDING,
                Order.Status.CONFIRMED,
                Order.Status.PROCESSING,
                Order.Status.SHIPPED,
            ]
        ).count(),
        'wishlist': Wishlist.objects.filter(user=request.user).count(),
        'addresses': Address.objects.filter(user=request.user).count(),
        'spent': orders.exclude(status=Order.Status.CANCELLED).aggregate(
            total=Sum('total')
        )['total']
        or Decimal('0.00'),
    }
    recent_orders = orders.prefetch_related('items').order_by('-created_at')[:3]
    return render(
        request,
        'home/dashboard.html',
        {
            'stats': stats,
            'recent_orders': recent_orders,
            'recent_addresses': Address.objects.filter(user=request.user)[:2],
        },
    )


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('dashboard')
    return render(request, 'home/profile.html', {'form': form})


@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'home/addresses.html', {'addresses': addresses})


@login_required
def address_create(request):
    form = AddressForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        if not request.user.addresses.exists():
            address.is_default = True
        address.save()
        messages.success(request, 'Delivery address saved.')
        return redirect('address_list')
    return render(
        request,
        'home/address_form.html',
        {'form': form, 'title': 'Add delivery address'},
    )


@login_required
def address_edit(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=address)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Delivery address updated.')
        return redirect('address_list')
    return render(
        request,
        'home/address_form.html',
        {'form': form, 'title': 'Edit delivery address'},
    )


@require_POST
@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    was_default = address.is_default
    address.delete()
    if was_default:
        replacement = Address.objects.filter(user=request.user).first()
        if replacement:
            replacement.is_default = True
            replacement.save(update_fields=['is_default'])
    messages.success(request, 'Delivery address removed.')
    return redirect('address_list')


@require_POST
@login_required
def address_set_default(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, 'Default delivery address updated.')
    return redirect('address_list')


@login_required
def change_password(request):
    form = StyledPasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Your password has been changed.')
        return redirect('dashboard')
    return render(request, 'home/password_change.html', {'form': form})
