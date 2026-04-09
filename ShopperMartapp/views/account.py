import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm

logger = logging.getLogger(__name__)

# -------------------- AUTH --------------------
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
    """Display logged-in user's profile."""
    return render(request, "account/profile.html")


@login_required
def profile_edit_view(request):
    """Edit user's profile and update information."""
    if request.method == "POST":
        uform = UserUpdateForm(request.POST, instance=request.user)
        pform = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if uform.is_valid() and pform.is_valid():
            uform.save()
            pform.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
    else:
        uform = UserUpdateForm(instance=request.user)
        pform = ProfileUpdateForm(instance=request.user.profile)

    return render(request, "account/profile_edit.html", {"uform": uform, "pform": pform})
