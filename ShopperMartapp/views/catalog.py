import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.http import HttpResponsePermanentRedirect
from django.db.models import Q, Case, When, Value, BooleanField
from ..models import Product, Category
from ..forms import ProductForm

logger = logging.getLogger(__name__)

# -------------------- SHOP --------------------
def shop_home(request):
    """Display all available products sorted by Image availability then Newest."""
    products = Product.objects.select_related('category').filter(available=True).annotate(
        has_image=Case(
            When(image__gt='', then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).order_by('-has_image', '-created_at')

    # Search filter
    query = request.GET.get("q", "")
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        if not products.exists():
            messages.error(request, f"No products found matching '{query}'. Showing latest collection instead.")

    categories = Category.objects.all()
    return render(request, "home.html", {
        "products": products,
        "categories": categories,
        "query": query,
    })


def public_store(request):
    """Public Store page with sidebar filtering and sorting."""
    # Start with all available products
    products = Product.objects.select_related('category').filter(available=True)
    categories = Category.objects.all()

    # Search query
    query = request.GET.get("q", "")
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    
    # Category filter
    category_slug = request.GET.get('category', '')
    if category_slug:
        products = products.filter(category__slug=category_slug)
        
    # Price filtering
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    if min_price and min_price.isdigit():
        products = products.filter(price__gte=min_price)
    if max_price and max_price.isdigit():
        products = products.filter(price__lte=max_price)
        
    # Sorting logic
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        products = products.order_by('-rating', '-reviews_count')
    else:  # newest
        products = products.order_by('-created_at')

    return render(request, "ShopperMartapp/public_store.html", {
        "products": products,
        "categories": categories,
        "selected_category": category_slug,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort_by,
        "query": query,
    })


def about_view(request):
    """Brand Story and Vision page."""
    return render(request, "about.html")


def contact_view(request):
    """Brand Support and Inquiry interface."""
    if request.method == "POST":
        messages.success(request, "Transmission Received: Our support registry will prioritize your inquiry within 24 hours.")
        return redirect("contact")
    return render(request, "contact.html")


def category_products(request, slug):
    """Display all products under a specific category. SEO-FRIENDLY: No login required to browse."""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.select_related('category').filter(category=category, available=True).annotate(
        has_image=Case(
            When(image__gt='', then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).order_by('-has_image', '-created_at')

    return render(request, "ShopperMartapp/category_products.html", {
        "category": category,
        "products": products
    })


def product_detail(request, slug):
    """Display detailed information about a single product. SEO-FRIENDLY: No login required to browse."""
    product = get_object_or_404(Product, slug=slug, available=True)
    
    # Related products logic
    related_products = Product.objects.filter(category=product.category, available=True).exclude(id=product.id)[:4]

    return render(request, "ShopperMartapp/product_detail.html", {
        "product": product,
        "related_products": related_products
    })


def product_detail_by_id(request, pk):
    """Redirect product detail by ID to canonical slug URL."""
    product = get_object_or_404(Product, pk=pk, available=True)
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
    """Delete a product. Staff only."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect("product_list")
    return render(request, "ShopperMartapp/product_confirm_delete.html", {"product": product})
