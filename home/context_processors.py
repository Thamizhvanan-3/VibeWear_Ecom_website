from .cart import cart_item_count
from .models import Wishlist


def cart_summary(request):
    context = {'cart_count': cart_item_count(request)}
    if request.user.is_authenticated:
        context['wishlist_count'] = Wishlist.objects.filter(
            user=request.user
        ).count()
    else:
        context['wishlist_count'] = 0
    return context
