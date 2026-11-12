from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .constants import calculate_shipping
from .models import (
    Address,
    Cart,
    CartItem,
    Category,
    Order,
    Product,
    ProductVariant,
    UserProfile,
    Wishlist,
)


class BaseStoreTest(TestCase):
    def make_user(self, username='buyer', email='buyer@example.com', password='Str0ngPass!2026'):
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name='Test',
            last_name='Buyer',
        )

    def first_product(self):
        return Product.objects.get(slug='denim-gray-shirt')

    def in_stock_variant(self, product=None):
        product = product or self.first_product()
        return (
            product.variants.filter(stock__gt=0)
            .select_related('size', 'color')
            .first()
        )

    def make_address(self, user):
        return Address.objects.create(
            user=user,
            full_name='Test Buyer',
            phone='+91 98765 43210',
            address_line1='12 Test Street',
            city='Chennai',
            state='Tamil Nadu',
            postal_code='600001',
            country='India',
            is_default=True,
        )

    def add_to_cart(self, client, product, variant, quantity=1):
        return client.post(
            reverse('add_to_cart', args=[product.slug]),
            {'variant_id': variant.pk, 'quantity': quantity},
        )


class AuthenticationTests(BaseStoreTest):
    def test_signup_creates_account_email_and_profile(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'newbuyer',
                'first_name': 'New',
                'last_name': 'Buyer',
                'email': 'NewBuyer@Example.com',
                'password1': 'Str0ngPass!2026',
                'password2': 'Str0ngPass!2026',
            },
        )
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='newbuyer')
        self.assertEqual(user.email, 'newbuyer@example.com')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_signup_rejects_duplicate_username_case_insensitively(self):
        self.make_user(username='ExistingUser')
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'existinguser',
                'email': 'fresh@example.com',
                'password1': 'Str0ngPass!2026',
                'password2': 'Str0ngPass!2026',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertEqual(User.objects.filter(username__iexact='existinguser').count(), 1)

    def test_signup_rejects_duplicate_email_case_insensitively(self):
        self.make_user(username='firstuser', email='same@example.com')
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'seconduser',
                'email': 'SAME@example.com',
                'password1': 'Str0ngPass!2026',
                'password2': 'Str0ngPass!2026',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email already exists')
        self.assertFalse(User.objects.filter(username='seconduser').exists())

    def test_login_with_username_or_email(self):
        user = self.make_user(username='loginuser', email='login@example.com')
        response = self.client.post(
            reverse('login'),
            {'username': 'loginuser', 'password': 'Str0ngPass!2026'},
        )
        self.assertRedirects(response, reverse('home'))
        self.client.get(reverse('logout'))
        response = self.client.post(
            reverse('login'),
            {'username': 'login@example.com', 'password': 'Str0ngPass!2026'},
        )
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_sends_email(self):
        self.make_user(email='reset@example.com')
        response = self.client.post(
            reverse('password_reset'), {'email': 'reset@example.com'}
        )
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('password', mail.outbox[0].subject.lower())

    def test_profile_edit_prevents_duplicate_email(self):
        user = self.make_user(username='profileuser', email='profile@example.com')
        self.make_user(username='otheruser', email='other@example.com')
        self.client.force_login(user)
        response = self.client.post(
            reverse('profile'),
            {
                'first_name': 'Updated',
                'last_name': 'Name',
                'email': 'other@example.com',
                'phone': '+91 98765 43210',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email already exists')

        response = self.client.post(
            reverse('profile'),
            {
                'first_name': 'Updated',
                'last_name': 'Name',
                'email': 'updated@example.com',
                'phone': '+91 98765 43210',
            },
        )
        self.assertRedirects(response, reverse('dashboard'))
        user.refresh_from_db()
        self.assertEqual(user.email, 'updated@example.com')
        self.assertEqual(user.profile.phone, '+91 98765 43210')

    def test_change_password_keeps_session(self):
        user = self.make_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse('change_password'),
            {
                'old_password': 'Str0ngPass!2026',
                'new_password1': 'An0therStr0ng!2026',
                'new_password2': 'An0therStr0ng!2026',
            },
        )
        self.assertRedirects(response, reverse('dashboard'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('An0therStr0ng!2026'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)


class CatalogTests(BaseStoreTest):
    def test_home_shop_and_detail_render(self):
        product = self.first_product()
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('shop')).status_code, 200)
        response = self.client.get(reverse('product_detail', args=[product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, product.name)

    def test_search_and_variant_filters(self):
        response = self.client.get(reverse('shop'), {'q': 'jacket'})
        self.assertContains(response, 'Black Jacket')
        self.assertNotContains(response, 'Classic White Shirt')

        response = self.client.get(reverse('shop'), {'size': 'M', 'color': 'Gray'})
        self.assertContains(response, 'Denim Gray Shirt')
        self.assertNotContains(response, 'Classic White Shirt')

        response = self.client.get(reverse('shop'), {'min_price': '100', 'max_price': '700'})
        self.assertContains(response, 'Floral Black Shirt')
        self.assertNotContains(response, 'Black Jacket')

    def test_category_and_subcategory_filter(self):
        response = self.client.get(reverse('shop'), {'category': 'shirts'})
        self.assertContains(response, 'Denim Gray Shirt')
        self.assertNotContains(response, 'Black Jacket')

        response = self.client.get(reverse('shop'), {'category': 'casual-shirts'})
        self.assertContains(response, 'Denim Gray Shirt')
        self.assertNotContains(response, 'Classic Green Shirt')

    def test_sorting_and_pagination(self):
        response = self.client.get(reverse('shop'), {'sort': 'price_asc'})
        page_products = list(response.context['page_obj'].object_list)
        prices = [product.price for product in page_products]
        self.assertEqual(prices, sorted(prices))

        response = self.client.get(reverse('home'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 2)

    def test_related_products(self):
        product = self.first_product()
        response = self.client.get(reverse('product_detail', args=[product.slug]))
        self.assertIn('related_products', response.context)


class CartTests(BaseStoreTest):
    def test_guest_cart_add_update_and_remove(self):
        product = self.first_product()
        variant = self.in_stock_variant(product)
        response = self.add_to_cart(self.client, product, variant, quantity=2)
        self.assertEqual(response.status_code, 302)
        item = CartItem.objects.get()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(Cart.objects.filter(user__isnull=True).count(), 1)

        response = self.client.get(reverse('cart'))
        self.assertEqual(response.context['cart_count'], 2)

        response = self.client.post(
            reverse('update_cart_item', args=[item.pk]), {'quantity': 1}
        )
        self.assertRedirects(response, reverse('cart'))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

        response = self.client.post(reverse('remove_cart_item', args=[item.pk]))
        self.assertRedirects(response, reverse('cart'))
        self.assertFalse(CartItem.objects.exists())

    def test_cart_respects_stock_and_quantity_limits(self):
        product = self.first_product()
        variant = self.in_stock_variant(product)
        self.add_to_cart(self.client, product, variant, quantity=999)
        item = CartItem.objects.get()
        self.assertLessEqual(item.quantity, variant.stock)
        self.assertLessEqual(item.quantity, 10)

    def test_add_out_of_stock_variant_is_rejected(self):
        product = self.first_product()
        variant = self.in_stock_variant(product)
        variant.stock = 0
        variant.save(update_fields=['stock'])
        self.add_to_cart(self.client, product, variant)
        self.assertFalse(CartItem.objects.exists())

    def test_guest_cart_merges_after_login(self):
        product = self.first_product()
        variant = self.in_stock_variant(product)
        self.add_to_cart(self.client, product, variant, quantity=2)
        self.assertTrue(Cart.objects.filter(user__isnull=True).exists())

        user = self.make_user()
        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'Str0ngPass!2026'},
        )
        self.assertRedirects(response, reverse('home'))
        user_cart = Cart.objects.get(user=user)
        self.assertEqual(user_cart.items.get().quantity, 2)
        self.assertFalse(Cart.objects.filter(user__isnull=True).exists())

    def test_logged_in_cart_persists_across_logout(self):
        user = self.make_user()
        self.client.force_login(user)
        product = self.first_product()
        variant = self.in_stock_variant(product)
        self.add_to_cart(self.client, product, variant, quantity=1)
        self.assertEqual(Cart.objects.get(user=user).items.count(), 1)

        self.client.get(reverse('logout'))
        self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'Str0ngPass!2026'},
        )
        self.assertEqual(Cart.objects.get(user=user).items.count(), 1)


class OrderTests(BaseStoreTest):
    def prepare_cart(self, quantity=2):
        user = self.make_user()
        address = self.make_address(user)
        self.client.force_login(user)
        product = self.first_product()
        variant = self.in_stock_variant(product)
        self.add_to_cart(self.client, product, variant, quantity=quantity)
        return user, address, product, variant

    def test_checkout_requires_login(self):
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_place_order_deducts_stock_and_clears_cart(self):
        user, address, product, variant = self.prepare_cart(quantity=2)
        stock_before = variant.stock
        sold_before = product.sold_count

        response = self.client.post(
            reverse('checkout'),
            {'address_id': address.pk, 'notes': 'Ring the bell', 'price': '1.00'},
        )
        order = Order.objects.get(user=user)
        self.assertRedirects(
            response,
            f"{reverse('order_detail', args=[order.order_number])}?placed=1",
        )
        expected_subtotal = product.price * 2
        expected_shipping = calculate_shipping(expected_subtotal)
        self.assertEqual(order.subtotal, expected_subtotal)
        self.assertEqual(order.shipping_fee, expected_shipping)
        self.assertEqual(order.total, expected_subtotal + expected_shipping)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.get().quantity, 2)
        variant.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(variant.stock, stock_before - 2)
        self.assertEqual(product.sold_count, sold_before + 2)
        self.assertTrue(order.stock_deducted)
        self.assertFalse(Cart.objects.get(user=user).items.exists())
        self.assertTrue(order.order_number.startswith('VW'))

    def test_checkout_revalidates_stock_and_keeps_cart(self):
        user, address, product, variant = self.prepare_cart(quantity=2)
        variant.stock = 0
        variant.save(update_fields=['stock'])
        response = self.client.post(reverse('checkout'), {'address_id': address.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(user=user).exists())
        self.assertTrue(Cart.objects.get(user=user).items.exists())

    def test_order_detail_is_private(self):
        user, address, product, variant = self.prepare_cart()
        self.client.post(reverse('checkout'), {'address_id': address.pk})
        order = Order.objects.get(user=user)
        self.client.get(reverse('logout'))
        other = self.make_user(username='other', email='other@example.com')
        self.client.force_login(other)
        response = self.client.get(
            reverse('order_detail', args=[order.order_number])
        )
        self.assertEqual(response.status_code, 404)

    def test_cancel_order_restores_stock(self):
        user, address, product, variant = self.prepare_cart(quantity=2)
        stock_before = variant.stock
        sold_before = product.sold_count
        self.client.post(reverse('checkout'), {'address_id': address.pk})
        order = Order.objects.get(user=user)
        variant.refresh_from_db()
        self.assertEqual(variant.stock, stock_before - 2)

        response = self.client.post(reverse('cancel_order', args=[order.order_number]))
        self.assertRedirects(
            response, reverse('order_detail', args=[order.order_number])
        )
        order.refresh_from_db()
        variant.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertFalse(order.stock_deducted)
        self.assertEqual(variant.stock, stock_before)
        self.assertEqual(product.sold_count, sold_before)

    def test_delivered_order_cannot_be_cancelled(self):
        user, address, product, variant = self.prepare_cart()
        self.client.post(reverse('checkout'), {'address_id': address.pk})
        order = Order.objects.get(user=user)
        order.set_status(Order.Status.DELIVERED)
        self.client.post(reverse('cancel_order', args=[order.order_number]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)

    def test_order_history_lists_only_own_orders(self):
        user, address, product, variant = self.prepare_cart()
        self.client.post(reverse('checkout'), {'address_id': address.pk})
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, Order.objects.get(user=user).order_number)


class WishlistTests(BaseStoreTest):
    def test_wishlist_requires_login(self):
        product = self.first_product()
        response = self.client.post(reverse('add_to_wishlist', args=[product.slug]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_add_prevents_duplicates_and_move_to_cart(self):
        user = self.make_user()
        self.client.force_login(user)
        product = self.first_product()
        variant = self.in_stock_variant(product)

        self.client.post(reverse('add_to_wishlist', args=[product.slug]))
        self.client.post(reverse('add_to_wishlist', args=[product.slug]))
        self.assertEqual(Wishlist.objects.filter(user=user, product=product).count(), 1)

        response = self.client.get(reverse('wishlist'))
        self.assertContains(response, product.name)

        wish = Wishlist.objects.get(user=user, product=product)
        response = self.client.post(
            reverse('move_wishlist_to_cart', args=[wish.pk]),
            {'variant_id': variant.pk},
        )
        self.assertRedirects(response, reverse('cart'))
        self.assertTrue(CartItem.objects.filter(cart__user=user, variant=variant).exists())
        self.assertFalse(Wishlist.objects.filter(pk=wish.pk).exists())

    def test_remove_from_wishlist(self):
        user = self.make_user()
        self.client.force_login(user)
        product = self.first_product()
        Wishlist.objects.create(user=user, product=product)
        response = self.client.post(reverse('remove_from_wishlist', args=[product.slug]))
        self.assertRedirects(response, reverse('wishlist'))
        self.assertFalse(Wishlist.objects.filter(user=user, product=product).exists())


class AdminTests(BaseStoreTest):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='adminuser', email='admin@example.com', password='Adm1nPass!2026'
        )
        self.client.force_login(self.admin)

    def test_admin_dashboard_and_changelists(self):
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Store overview')
        self.assertContains(response, 'Low stock alerts')
        self.assertEqual(self.client.get(reverse('admin:home_product_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:home_order_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 200)

    def test_low_stock_filter(self):
        response = self.client.get(
            reverse('admin:home_product_changelist'), {'stock_level': 'low'}
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_cancel_action_restores_stock(self):
        user = self.make_user()
        address = self.make_address(user)
        buyer = Client()
        buyer.force_login(user)
        product = self.first_product()
        variant = self.in_stock_variant(product)
        self.add_to_cart(buyer, product, variant, quantity=2)
        buyer.post(reverse('checkout'), {'address_id': address.pk})
        order = Order.objects.get(user=user)
        order.set_status(Order.Status.CONFIRMED)
        variant.refresh_from_db()
        stock_after_order = variant.stock

        response = self.client.post(
            reverse('admin:home_order_changelist'),
            {
                'action': 'mark_cancelled',
                '_selected_action': [order.pk],
                'index': '0',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(variant.stock, stock_after_order + 2)

    def test_admin_product_change_form(self):
        product = self.first_product()
        response = self.client.get(
            reverse('admin:home_product_change', args=[product.pk])
        )
        self.assertEqual(response.status_code, 200)


class SecurityTests(BaseStoreTest):
    def test_post_without_csrf_token_is_rejected(self):
        product = self.first_product()
        variant = self.in_stock_variant(product)
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse('add_to_cart', args=[product.slug]),
            {'variant_id': variant.pk, 'quantity': 1},
        )
        self.assertEqual(response.status_code, 403)

    def test_customer_pages_require_login(self):
        for url in (
            reverse('dashboard'),
            reverse('profile'),
            reverse('address_list'),
            reverse('wishlist'),
            reverse('order_history'),
            reverse('change_password'),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response['Location'])
