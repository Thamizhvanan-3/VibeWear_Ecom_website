from datetime import timedelta
from decimal import Decimal

from django.db import migrations
from django.utils import timezone


def seed_catalog(apps, schema_editor):
    Category = apps.get_model('home', 'Category')
    Size = apps.get_model('home', 'Size')
    Color = apps.get_model('home', 'Color')
    Product = apps.get_model('home', 'Product')
    ProductImage = apps.get_model('home', 'ProductImage')
    ProductVariant = apps.get_model('home', 'ProductVariant')
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('home', 'UserProfile')

    # Existing accounts keep working and receive a profile row.
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)

    shirts, _ = Category.objects.get_or_create(
        slug='shirts', defaults={'name': 'Shirts'}
    )
    casual, _ = Category.objects.get_or_create(
        slug='casual-shirts',
        defaults={'name': 'Casual Shirts', 'parent': shirts},
    )
    formal, _ = Category.objects.get_or_create(
        slug='formal-shirts',
        defaults={'name': 'Formal Shirts', 'parent': shirts},
    )
    jackets, _ = Category.objects.get_or_create(
        slug='jackets', defaults={'name': 'Jackets'}
    )
    winter, _ = Category.objects.get_or_create(
        slug='winter-jackets',
        defaults={'name': 'Winter Jackets', 'parent': jackets},
    )

    size_names = ['S', 'M', 'L', 'XL', 'XXL']
    sizes = {}
    for order, name in enumerate(size_names):
        size, _ = Size.objects.get_or_create(
            name=name, defaults={'sort_order': order}
        )
        sizes[name] = size

    color_data = {
        'Black': '#000000',
        'White': '#ffffff',
        'Gray': '#808080',
        'Green': '#2e7d32',
        'Red': '#b31414',
        'Navy': '#1a237e',
        'Blue': '#1565c0',
        'Beige': '#d7c4a3',
    }
    colors = {}
    for name, hex_code in color_data.items():
        color, _ = Color.objects.get_or_create(
            name=name, defaults={'hex_code': hex_code}
        )
        colors[name] = color

    products = [
        {
            'name': 'Denim Gray Shirt',
            'slug': 'denim-gray-shirt',
            'category': casual,
            'price': '699.00',
            'original_price': '999.00',
            'image': 'home/image5.avif',
            'sizes': ['S', 'M', 'L', 'XL'],
            'colors': ['Gray', 'Navy'],
            'featured': True,
            'new': False,
            'sold': 42,
            'age': 24,
            'description': (
                'A relaxed denim shirt with a soft washed finish. Wear it '
                'buttoned with chinos or open over a plain tee.'
            ),
        },
        {
            'name': 'Floral Black Shirt',
            'slug': 'floral-black-shirt',
            'category': casual,
            'price': '599.00',
            'original_price': '899.00',
            'image': 'home/image2.avif',
            'sizes': ['S', 'M', 'L', 'XL'],
            'colors': ['Black', 'White'],
            'featured': True,
            'new': True,
            'sold': 65,
            'age': 6,
            'description': (
                'A statement floral print on a breathable black base. '
                'Designed for evenings out and weekend plans.'
            ),
        },
        {
            'name': 'Classic Green Shirt',
            'slug': 'classic-green-shirt',
            'category': formal,
            'price': '799.00',
            'original_price': '1099.00',
            'image': 'home/image3.avif',
            'sizes': ['M', 'L', 'XL', 'XXL'],
            'colors': ['Green', 'White'],
            'featured': True,
            'new': False,
            'sold': 31,
            'age': 40,
            'description': (
                'A clean, structured shirt in a deep forest green. A sharp '
                'choice for workdays and formal occasions.'
            ),
        },
        {
            'name': 'Printed Red Shirt',
            'slug': 'printed-red-shirt',
            'category': casual,
            'price': '899.00',
            'original_price': '1299.00',
            'image': 'home/image4.avif',
            'sizes': ['S', 'M', 'L'],
            'colors': ['Red', 'Black'],
            'featured': False,
            'new': True,
            'sold': 18,
            'age': 3,
            'description': (
                'Bold red tones with an art-inspired print. Cut for a '
                'comfortable fit that moves with you.'
            ),
        },
        {
            'name': 'Denim Blue Shirt',
            'slug': 'denim-blue-shirt',
            'category': casual,
            'price': '749.00',
            'original_price': '999.00',
            'image': 'home/image5.avif',
            'sizes': ['M', 'L', 'XL'],
            'colors': ['Blue', 'Gray'],
            'featured': False,
            'new': True,
            'sold': 27,
            'age': 2,
            'description': (
                'Mid-weight denim in a versatile blue wash. Layer it or wear '
                'it on its own all year round.'
            ),
        },
        {
            'name': 'Black Jacket',
            'slug': 'black-jacket',
            'category': winter,
            'price': '1399.00',
            'original_price': '1999.00',
            'image': 'home/image6.avif',
            'sizes': ['M', 'L', 'XL', 'XXL'],
            'colors': ['Black', 'Gray'],
            'featured': True,
            'new': False,
            'sold': 88,
            'age': 60,
            'description': (
                'Our best-selling everyday jacket. Warm, lightweight and '
                'easy to pair with everything in your wardrobe.'
            ),
        },
        {
            'name': 'Slim Fit Jacket',
            'slug': 'slim-fit-jacket',
            'category': jackets,
            'price': '1199.00',
            'original_price': '1699.00',
            'image': 'home/image7.avif',
            'sizes': ['S', 'M', 'L', 'XL'],
            'colors': ['Navy', 'Black'],
            'featured': False,
            'new': True,
            'sold': 54,
            'age': 4,
            'description': (
                'A sharp slim-fit layer with a modern silhouette. Ideal for '
                'cooler evenings and smart-casual looks.'
            ),
        },
        {
            'name': 'Classic White Shirt',
            'slug': 'classic-white-shirt',
            'category': formal,
            'price': '649.00',
            'original_price': '899.00',
            'image': 'home/image1.avif',
            'sizes': ['S', 'M', 'L', 'XL'],
            'colors': ['White', 'Beige'],
            'featured': False,
            'new': False,
            'sold': 73,
            'age': 80,
            'description': (
                'The wardrobe essential: a crisp white shirt with a clean '
                'collar and comfortable regular fit.'
            ),
        },
        {
            'name': 'Urban Overshirt',
            'slug': 'urban-overshirt',
            'category': casual,
            'price': '999.00',
            'original_price': '1399.00',
            'image': 'home/image3.avif',
            'sizes': ['M', 'L', 'XL'],
            'colors': ['Green', 'Gray', 'Black'],
            'featured': False,
            'new': True,
            'sold': 12,
            'age': 1,
            'description': (
                'A roomy overshirt built for layering. Roomy pockets and a '
                'soft brushed finish make it an everyday favourite.'
            ),
        },
    ]

    stock_pattern = [14, 8, 3, 0, 21, 6, 11]
    for product_index, data in enumerate(products):
        product, created = Product.objects.get_or_create(
            slug=data['slug'],
            defaults={
                'name': data['name'],
                'category': data['category'],
                'description': data['description'],
                'price': Decimal(data['price']),
                'original_price': Decimal(data['original_price']),
                'is_active': True,
                'is_featured': data['featured'],
                'is_new_arrival': data['new'],
                'sold_count': data['sold'],
            },
        )
        if not created:
            continue

        Product.objects.filter(pk=product.pk).update(
            created_at=timezone.now() - timedelta(days=data['age'])
        )
        ProductImage.objects.create(
            product=product,
            static_path=data['image'],
            alt_text=data['name'],
            is_primary=True,
            sort_order=0,
        )

        variant_index = 0
        for size_name in data['sizes']:
            for color_name in data['colors']:
                stock = stock_pattern[
                    (product_index + variant_index) % len(stock_pattern)
                ]
                sku = (
                    f"{data['slug'].upper()[:20]}-{size_name}-{color_name}"
                ).upper()
                ProductVariant.objects.get_or_create(
                    product=product,
                    size=sizes[size_name],
                    color=colors[color_name],
                    defaults={'stock': stock, 'sku': sku},
                )
                variant_index += 1


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]
