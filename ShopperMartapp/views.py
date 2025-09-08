from django.urls import reverse
from django.http import HttpResponsePermanentRedirect

def product_detail_by_id(request, pk):
    """Redirect product detail by ID to canonical slug URL."""
    product = get_object_or_404(Product, pk=pk, available=True)
    canonical_url = reverse("product_detail", kwargs={"slug": product.slug})
    return HttpResponsePermanentRedirect(canonical_url)
# ShopperMartapp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm, ProductForm
from .models import Product, Category, Cart, CartItem, Order, OrderItem


# -------------------- SHOP --------------------
def shop_home(request):
    """Display all available products and categories on the homepage."""
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()
    return render(request, "home.html", {
        "products": products,
        "categories": categories
    })


def category_products(request, slug):
    """Display all products under a specific category."""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, available=True)
    return render(request, "ShopperMartapp/category_products.html", {
        "category": category,
        "products": products
    })


def product_detail(request, slug):
    """Display detailed information about a single product."""
    product = get_object_or_404(Product, slug=slug, available=True)
    return render(request, "ShopperMartapp/product_detail.html", {
        "product": product
    })


# -------------------- AUTH --------------------
def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect("shop_home")

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


# -------------------- CART --------------------
@login_required
def cart_view(request):
    """Show current user's cart with subtotal and total."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related("product")  # all items in the cart

    total = 0
    for item in cart_items:
        item.subtotal = item.product.price * item.quantity  # add subtotal dynamically
        total += item.subtotal

    return render(request, "ShopperMartapp/cart.html", {
        "cart": cart,
        "cart_items": cart_items,
        "total": total,
    })




@login_required
def add_to_cart(request, product_id):
    """Add product to cart."""
    product = get_object_or_404(Product, id=product_id, available=True)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{product.name} added to cart.")
    return redirect("cart")


@login_required
def update_cart(request, item_id):
    """Update quantity of a cart item."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, f"{cart_item.product.name} quantity updated.")
        else:
            cart_item.delete()
            messages.info(request, f"{cart_item.product.name} removed from cart.")
    return redirect("cart")


@login_required
def remove_from_cart(request, item_id):
    """Remove product from cart."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.info(request, f"{product_name} removed from cart.")
    return redirect("cart")


# -------------------- CHECKOUT & ORDERS --------------------
@login_required
def checkout(request):
    """Checkout process - create an order from cart items."""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.select_related('product').all()
    total = sum(item.quantity * item.product.price for item in cart_items)

    if request.method == "POST":
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect("cart")

        order = Order.objects.create(user=request.user, total=0)
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
        order.total = total
        order.save()

        # clear cart
        cart.items.all().delete()

        messages.success(request, "Order placed successfully!")
        return redirect("my_orders")

    # GET request: show checkout page
    return render(request, "ShopperMartapp/checkout.html", {
        "cart_items": cart_items,
        "total": total,
        # add 'form' if you use a form in the template
    })


@login_required
def my_orders(request):
    """List all orders of the logged-in user."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "ShopperMartapp/my_orders.html", {"orders": orders})


# -------------------- PRODUCT MANAGEMENT --------------------
@login_required
def product_list(request):
    """Show all products + allow search + filter + add new product."""
    query = request.GET.get("q", "")
    category_slug = request.GET.get("category", "")

    products = Product.objects.all()
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


@login_required
def product_update(request, pk):
    """Update a product."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect("product_list")
    else:
        form = ProductForm(instance=product)

    return render(request, "products.html", {"form": form, "edit_mode": True})


@login_required
def product_delete(request, pk):
    """Delete a product."""
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.info(request, "Product deleted successfully.")
    return redirect("product_list")
