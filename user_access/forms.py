from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .constants import ROLE_CHOICES


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email", "role")


class SignInForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True}))


class OwnerUserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email")

    def clean_password(self):
        password = self.cleaned_data["password"]
        user = User(
            username=self.cleaned_data.get("username", ""),
            first_name=self.cleaned_data.get("first_name", ""),
            last_name=self.cleaned_data.get("last_name", ""),
            email=self.cleaned_data.get("email", ""),
        )
        validate_password(password, user=user)
        return password


class OwnerUserRoleForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES)
