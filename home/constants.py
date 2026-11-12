from decimal import Decimal

SHIPPING_FEE = Decimal('49.00')
FREE_SHIPPING_THRESHOLD = Decimal('999.00')
LOW_STOCK_THRESHOLD = 5
MAX_ITEM_QUANTITY = 10


def calculate_shipping(subtotal):
    subtotal = Decimal(subtotal or 0)
    if subtotal <= 0 or subtotal >= FREE_SHIPPING_THRESHOLD:
        return Decimal('0.00')
    return SHIPPING_FEE
