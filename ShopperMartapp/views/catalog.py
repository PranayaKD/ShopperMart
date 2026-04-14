from django.shortcuts import render, redirect, get_object_or_404
from django_ratelimit.decorators import ratelimit
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import HttpResponsePermanentRedirect
from django.db.models import Q, Case, When, Value, BooleanField
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
from ..models import Product, Category, Review, Wishlist


# -------------------- SHOP --------------------
def shop_home(request):
    """Display all available products with high-performance filtering and rate-limited search."""
    query = request.GET.get("q", "").strip()
    
    # 50+ Edge Case: Search Rate Limiting (Case #12)
    import time
    now = time.time()
    last_search = request.session.get('last_search_time', 0)
    search_count = request.session.get('search_count', 0)
    
    # Reset count if last search was > 60s ago
    if now - last_search > 60:
        search_count = 0
    
    if query:
        if search_count > 10:
            messages.warning(request, "Slow down a bit! You've made quite a few searches. Please wait a minute before trying again.")
            query = "" # Silently ignore or throttle
        else:
            request.session['search_count'] = search_count + 1
            request.session['last_search_time'] = now

    # Using optimized QuerySet methods
    products = Product.objects.available().with_category().with_image_status().search(query).sort_by('newest')

    if query and not products.exists():
        messages.error(request, f"No products found matching '{query}'. Showing latest collection instead.")

    return render(request, "home.html", {
        "products": products,
        "categories": Category.objects.all(),
        "query": query,
        "wishlisted_ids": Wishlist.get_product_ids_for_user(request.user),
    })


def public_store(request):
    """Public Store page with sidebar filtering and sorting."""
    # Get parameters
    query = request.GET.get("q", "")
    category_slug = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', 'newest')

    # Build optimized QuerySet
    products = Product.objects.available().with_category().search(query)
    
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    # Price filtering (Fixed: Use Decimal for precision)
    try:
        if min_price:
            products = products.filter(price__gte=Decimal(min_price))
        if max_price:
            products = products.filter(price__lte=Decimal(max_price))
    except (InvalidOperation, ValueError):
        messages.error(request, "Invalid price filter range.")
        
    products = products.sort_by(sort_by)

    return render(request, "ShopperMartapp/public_store.html", {
        "products": products,
        "categories": Category.objects.all(),
        "selected_category": category_slug,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort_by,
        "query": query,
        "wishlisted_ids": Wishlist.get_product_ids_for_user(request.user),
    })


def about_view(request):
    """Brand Story and Vision page."""
    return render(request, "about.html")


@ratelimit(key='ip', rate='3/m', block=True)
def contact_view(request):
    """Brand Support and Inquiry interface. Sends email to admin (AS REQUESTED)."""
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()
        
        # 1. RIGOROUS VALIDATION
        if not all([name, email, message]):
            messages.error(request, "All fields (Name, Email, Message) are required.")
            return redirect("contact")

        # Email Format Check
        try:
            validate_email(email)
        except ValidationError:
            logger.warning(f"ContactValidationFailure: Invalid email format attempted ({email[:5]}...)")
            messages.error(request, "Please provide a valid email address.")
            return redirect("contact")

        # Length Constraints
        if len(name) > 100:
            messages.error(request, "Name is too long (max 100 characters).")
            return redirect("contact")
        if len(email) > 254:
            messages.error(request, "Email address is too long.")
            return redirect("contact")
        if len(message) > 5000:
            messages.error(request, "Message is too long (max 5000 characters).")
            return redirect("contact")

        # 2. SEND EMAIL TO ADMIN
        subject = f"New ShopperMart Contact Inquiry from {name}"
        email_body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        
        try:
            send_mail(
                subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER], # Admin email
                fail_silently=False,
            )
            messages.success(request, "Message sent! Our team will get back to you within 24 hours.")
        except Exception as e:
            logger.error(f"ContactMailError: {e}")
            messages.warning(request, "Message processed, but email notification failed. We will check our logs.")
            
        return redirect("contact")
    return render(request, "contact.html")


def category_products(request, slug):
    """Display all products under a specific category. SEO-FRIENDLY: No login required to browse."""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.available().filter(category=category).with_category().with_image_status().sort_by('newest')

    return render(request, "ShopperMartapp/category_products.html", {
        "category": category,
        "products": products,
        "wishlisted_ids": Wishlist.get_product_ids_for_user(request.user),
    })


def product_detail(request, slug):
    """Display detailed information about a single product. SEO-FRIENDLY: No login required to browse."""
    product = get_object_or_404(Product.objects.with_category(), slug=slug, available=True)
    
    # Related products logic (optimized)
    related_products = Product.objects.available().filter(category=product.category).exclude(id=product.id)[:4]

    # Reviews (approved only, with related users)
    approved_reviews = product.reviews.filter(is_approved=True).select_related('user')

    # User's own review
    user_review = None
    if request.user.is_authenticated:
        user_review = product.reviews.filter(user=request.user).first()

    return render(request, "ShopperMartapp/product_detail.html", {
        "product": product,
        "related_products": related_products,
        "approved_reviews": approved_reviews,
        "user_review": user_review,
    })


def product_detail_by_id(request, pk):
    """Redirect product detail by ID to canonical slug URL."""
    try:
        product = get_object_or_404(Product, pk=pk, available=True)
    except ValidationError:
        return render(request, "404.html", status=404)
    canonical_url = reverse("product_detail", kwargs={"slug": product.slug})
    return HttpResponsePermanentRedirect(canonical_url)


# -------------------- PRODUCT MANAGEMENT --------------------
@staff_member_required
def product_list(request):
    """Show all products + allow search + filter + add new product. Staff only."""
    query = request.GET.get("q", "")
    category_slug = request.GET.get("category", "")

    products = Product.objects.select_related('category').all()
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)

    categories = Category.objects.all()
    form = ProductForm()

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully.")
            return redirect("product_list")

    return render(request, "products.html", {
        "products": products,
        "categories": categories,
        "form": form,
        "query": query,
        "selected_category": category_slug,
    })


@staff_member_required
def product_update(request, pk):
    """Update a product. Staff only."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect("product_list")
    else:
        form = ProductForm(instance=product)
    
    return render(request, "ShopperMartapp/product_form.html", {"form": form, "title": "Update product"})


@staff_member_required
def product_delete(request, pk):
    """Soft-delete a product to maintain integrity of historical orders."""
    try:
        product = get_object_or_404(Product, pk=pk)
    except ValidationError:
        return render(request, "404.html", status=404)
        
    if request.method == "POST":
        product.is_deleted = True
        product.save()
        messages.success(request, f"Product '{product.name}' archived successfully (Soft Delete).")
        return redirect("product_list")
    return render(request, "ShopperMartapp/product_confirm_delete.html", {"product": product})


# -------------------- REVIEWS --------------------
@login_required
@require_POST
@ratelimit(key='user', rate='5/h', block=True)
def submit_review(request, product_id):
    """Submit or update a product review. One review per user per product."""
    try:
        product = get_object_or_404(Product, id=product_id)
    except ValidationError:
        return render(request, "404.html", status=404)
    
    try:
        rating = int(request.POST.get('rating', 0))
        if not (1 <= rating <= 5):
            messages.error(request, "Please select a rating between 1 and 5.")
            return redirect('product_detail', slug=product.slug)
    except (ValueError, TypeError):
        messages.error(request, "Invalid rating.")
        return redirect('product_detail', slug=product.slug)

    comment = request.POST.get('comment', '').strip()
    if len(comment) < 10:
        messages.error(request, "Review must be at least 10 characters long.")
        return redirect('product_detail', slug=product.slug)

    # Create or update (one review per user per product)
    review, created = Review.objects.update_or_create(
        product=product,
        user=request.user,
        defaults={
            'rating': rating,
            'comment': comment,
            'is_approved': False,  # Reset approval on update
        }
    )
    
    if created:
        messages.success(request, "Your review has been submitted and is pending approval.")
    else:
        messages.success(request, "Your review has been updated and is pending re-approval.")
    
    return redirect('product_detail', slug=product.slug)


# -------------------- WISHLIST --------------------
@login_required
def wishlist_view(request):
    """Display the user's saved objects."""
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return render(request, "ShopperMartapp/wishlist.html", {
        "wishlist": wishlist,
        "products": wishlist.products.all()
    })


@login_required
@require_POST
def toggle_wishlist(request, product_id):
    """Toggle a product in the user's wishlist via AJAX or POST."""
    from django.http import JsonResponse
    try:
        product = get_object_or_404(Product, id=product_id)
    except ValidationError:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return JsonResponse({"error": "Invalid Product ID"}, status=400)
        return render(request, "404.html", status=404)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    
    if wishlist.products.filter(id=product_id).exists():
        wishlist.products.remove(product)
        status = "removed"
    else:
        wishlist.products.add(product)
        status = "added"
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            "status": status,
            "item_count": wishlist.item_count
        })
    
    messages.success(request, f"Product {'saved to' if status == 'added' else 'removed from'} your wishlist.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def error_404_view(request, exception):
    """Custom 404 handler with brand theme."""
    return render(request, '404.html', status=404)


def error_500_view(request):
    """Custom 500 handler with brand theme."""
    return render(request, '500.html', status=500)
