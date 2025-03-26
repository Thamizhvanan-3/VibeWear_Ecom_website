from django.shortcuts import render,redirect
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.core.mail import send_mail 

def home(request):
    # List of shirts with image, name, and price
    shirts = [
        {'image': 'image5.avif', 'name': 'Denim Gray Shirt', 'price': 699},
        {'image': 'image2.avif', 'name': 'Floral Black Shirt', 'price': 599},
        {'image': 'image3.avif', 'name': 'Classic Green Shirt', 'price': 799},
        {'image': 'image4.avif', 'name': 'Printed Red Shirt', 'price': 899},
        {'image': 'image5.avif', 'name': 'Denim Gray Shirt', 'price': 699},
        {'image': 'image6.avif', 'name': 'Black Jacket', 'price': 1399},
        {'image': 'image7.avif', 'name': 'Slim Fit Jacket', 'price': 1199},
        {'image': 'image5.avif', 'name': 'Denim Gray Shirt', 'price': 699},
        {'image': 'image2.avif', 'name': 'Floral Black Shirt', 'price': 599},
    ]
    paginator = Paginator(shirts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    return render(request, 'home/home.html', {'page_obj': page_obj})

def about(request):
    return render(request,'home/about.html')

def contact(request):
    return render(request,'home/contact.html')

def contact_submit(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        message = request.POST['message']
        
        # Example: Sending an email (optional)
        send_mail(
            subject=f"Message from {name}",
            message=message,
            from_email=email,
            recipient_list=['admin@vibewear.com'],  # Replace with your admin email
        )
        return HttpResponse("Thank you for contacting us! We'll get back to you soon.")
    return HttpResponse("Invalid request.")

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

# Signup View
def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            return render(request, 'home/signup.html', {'error': 'Passwords do not match'})

        if User.objects.filter(username=username).exists():
            return render(request, 'home/signup.html', {'error': 'Username already exists'})

        user = User.objects.create_user(username=username, password=password)
        login(request, user)  # Automatically log in the user after signup
        return redirect('home')

    return render(request, 'home/signup.html')

# Login View
def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'home/login.html', {'error': 'Invalid username or password'})

    return render(request, 'home/login.html')

# Logout View
def user_logout(request):
    logout(request)
    return redirect('home')
