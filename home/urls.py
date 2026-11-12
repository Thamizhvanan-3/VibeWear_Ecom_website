from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),
    path('shop/', views.shop, name='shop'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/<slug:slug>/', views.add_to_cart, name='add_to_cart'),
    path(
        'cart/item/<int:item_id>/update/',
        views.update_cart_item,
        name='update_cart_item',
    ),
    path(
        'cart/item/<int:item_id>/remove/',
        views.remove_cart_item,
        name='remove_cart_item',
    ),
    path('wishlist/', views.wishlist, name='wishlist'),
    path(
        'wishlist/add/<slug:slug>/', views.add_to_wishlist, name='add_to_wishlist'
    ),
    path(
        'wishlist/remove/<slug:slug>/',
        views.remove_from_wishlist,
        name='remove_from_wishlist',
    ),
    path(
        'wishlist/<int:item_id>/move-to-cart/',
        views.move_wishlist_to_cart,
        name='move_wishlist_to_cart',
    ),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path(
        'orders/<str:order_number>/cancel/',
        views.cancel_order,
        name='cancel_order',
    ),
    path('account/', views.dashboard, name='dashboard'),
    path('account/profile/', views.profile, name='profile'),
    path('account/addresses/', views.address_list, name='address_list'),
    path('account/addresses/add/', views.address_create, name='address_create'),
    path(
        'account/addresses/<int:pk>/edit/',
        views.address_edit,
        name='address_edit',
    ),
    path(
        'account/addresses/<int:pk>/delete/',
        views.address_delete,
        name='address_delete',
    ),
    path(
        'account/addresses/<int:pk>/default/',
        views.address_set_default,
        name='address_set_default',
    ),
    path(
        'account/password/',
        views.change_password,
        name='change_password',
    ),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
]
