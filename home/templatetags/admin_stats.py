from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.template import Library

from ..constants import LOW_STOCK_THRESHOLD
from ..models import Order, Product, ProductVariant

register = Library()
User = get_user_model()


@register.simple_tag
def admin_dashboard_stats():
    revenue = (
        Order.objects.exclude(status=Order.Status.CANCELLED).aggregate(
            total=Sum('total')
        )['total']
        or Decimal('0.00')
    )
    open_statuses = [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
    ]
    low_stock = (
        ProductVariant.objects.filter(
            stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD
        )
        .select_related('product', 'size', 'color')
        .order_by('stock', 'product__name')[:8]
    )
    return {
        'product_count': Product.objects.count(),
        'active_product_count': Product.objects.filter(is_active=True).count(),
        'customer_count': User.objects.filter(is_staff=False).count(),
        'order_count': Order.objects.count(),
        'pending_order_count': Order.objects.filter(status__in=open_statuses).count(),
        'revenue': revenue,
        'low_stock_count': ProductVariant.objects.filter(
            stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD
        ).count(),
        'out_of_stock_count': ProductVariant.objects.filter(stock=0).count(),
        'low_stock_variants': low_stock,
        'low_stock_threshold': LOW_STOCK_THRESHOLD,
    }
