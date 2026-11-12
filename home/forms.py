from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from .models import Address, UserProfile

phone_validator = RegexValidator(
    regex=r'^\+?[0-9][0-9\s-]{6,18}$',
    message='Enter a valid phone number.',
)


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        max_length=254,
        widget=forms.EmailInput(
            attrs={'placeholder': 'Email address', 'autocomplete': 'email'}
        ),
    )
    first_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Last name'}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(
            {'placeholder': 'Username', 'autocomplete': 'username'}
        )
        self.fields['password1'].widget.attrs.update(
            {'placeholder': 'Password', 'autocomplete': 'new-password'}
        )
        self.fields['password2'].widget.attrs.update(
            {'placeholder': 'Confirm password', 'autocomplete': 'new-password'}
        )
        self.fields['username'].help_text = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('An account with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Username or email',
                'autocomplete': 'username',
                'autofocus': True,
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'placeholder': 'Password', 'autocomplete': 'current-password'}
        )
    )
    error_messages = {
        'invalid_login': 'Please enter a correct username/email and password.',
        'inactive': 'This account is inactive.',
    }


class ProfileForm(forms.Form):
    first_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Last name'}),
    )
    email = forms.EmailField(
        required=True,
        max_length=254,
        widget=forms.EmailInput(
            attrs={'placeholder': 'Email address', 'autocomplete': 'email'}
        ),
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        validators=[phone_validator],
        widget=forms.TextInput(
            attrs={'placeholder': 'Phone number', 'autocomplete': 'tel'}
        ),
    )
    date_of_birth = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None and not self.is_bound:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            self.initial.update(
                {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone': profile.phone,
                    'date_of_birth': profile.date_of_birth,
                }
            )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        duplicates = User.objects.filter(email__iexact=email)
        if self.user is not None:
            duplicates = duplicates.exclude(pk=self.user.pk)
        if duplicates.exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self):
        user = self.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.save(update_fields=['first_name', 'last_name', 'email'])
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = self.cleaned_data['phone']
        profile.date_of_birth = self.cleaned_data['date_of_birth']
        profile.save()
        return user


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            'label',
            'full_name',
            'phone',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'country',
            'is_default',
        )
        widgets = {
            'label': forms.TextInput(attrs={'placeholder': 'Home, Office...'}),
            'full_name': forms.TextInput(attrs={'placeholder': 'Full name'}),
            'phone': forms.TextInput(
                attrs={'placeholder': 'Phone number', 'autocomplete': 'tel'}
            ),
            'address_line1': forms.TextInput(
                attrs={'placeholder': 'House / street address'}
            ),
            'address_line2': forms.TextInput(
                attrs={'placeholder': 'Apartment, landmark (optional)'}
            ),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'placeholder': 'State'}),
            'postal_code': forms.TextInput(
                attrs={'placeholder': 'Postal code', 'autocomplete': 'postal-code'}
            ),
            'country': forms.TextInput(attrs={'placeholder': 'Country'}),
        }


class CheckoutNotesForm(forms.Form):
    notes = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': 'Delivery instructions (optional)',
            }
        ),
    )


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update(
            {'placeholder': 'Current password', 'autocomplete': 'current-password'}
        )
        self.fields['new_password1'].widget.attrs.update(
            {'placeholder': 'New password', 'autocomplete': 'new-password'}
        )
        self.fields['new_password2'].widget.attrs.update(
            {'placeholder': 'Confirm new password', 'autocomplete': 'new-password'}
        )
        for field in self.fields.values():
            field.help_text = ''


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=120, widget=forms.TextInput(attrs={'placeholder': 'Your Name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Your Email'})
    )
    message = forms.CharField(
        max_length=5000,
        widget=forms.Textarea(attrs={'placeholder': 'Your Message', 'rows': 5}),
    )
