import logging
from django.shortcuts import render, redirect, get_object_or_404
from django_ratelimit.decorators import ratelimit
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from ..forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm
from ..models import Profile

logger = logging.getLogger(__name__)

# -------------------- AUTH --------------------
def google_login_dispatcher(request):
    """
    Dispatches Google Sign-In:
    - If Google OAuth keys are set in settings/env, delegates to allauth's /accounts/google/login/
    - If keys are not configured, informs the user and redirects to standard login.
    """
    google_client_id = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('google', {}).get('APP', {}).get('client_id', '')
    
    # If a real client id is set (not empty, not placeholder)
    if google_client_id and google_client_id not in ('', 'your-client-id'):
        return redirect('google_login')

    messages.info(request, "Google Sign-In is not currently configured. Please sign in with your username and password or register an account.")
    return redirect('login')


@ratelimit(key='ip', rate='5/m', block=True)
def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect("home")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created! You can now log in.")
            return redirect("login")
    else:
        form = UserRegistrationForm()

    return render(request, "auth/register.html", {"form": form})


# -------------------- PROFILE --------------------
@login_required
def profile_view(request):
    """Unified user profile overview and in-place profile editing."""
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        uform = UserUpdateForm(request.POST, instance=request.user)
        pform = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if uform.is_valid() and pform.is_valid():
            uform.save()
            pform.save()
            messages.success(request, "🎉 Your profile has been updated successfully!")
            return redirect("profile")
        else:
            messages.error(request, "Please check the highlighted errors below and try again.")
    else:
        uform = UserUpdateForm(instance=request.user)
        pform = ProfileUpdateForm(instance=profile)

    return render(request, "account/profile.html", {
        "profile": profile,
        "uform": uform,
        "pform": pform,
    })


@login_required
def profile_edit_view(request):
    """Redirects to unified profile page with edit section active."""
    return redirect(f"{reverse('profile')}#edit-profile")
