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
from django.contrib.auth import login
from django.db.models import Q, Case, When, Value, BooleanField
from .forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm, ProductForm, CheckoutForm
from .models import Product, Category, Cart, CartItem, Order, OrderItem


# -------------------- SHOP --------------------
def shop_home(request):
    """Display all available products sorted by Image availability then Newest."""
    products = Product.objects.filter(available=True).annotate(
        has_image=Case(
            When(image__gt='', then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).order_by('-has_image', '-created_at')

    categories = Category.objects.all()
    return render(request, "home.html", {
        "products": products,
        "categories": categories
    })


def category_products(request, slug):
    """Display all products under a specific category, sorted by Image then Newest."""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, available=True).annotate(
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
    """Display detailed information about a single product."""
    product = get_object_or_404(Product, slug=slug, available=True)
    
    # Related products logic
    related_products = Product.objects.filter(category=product.category, available=True).exclude(id=product.id)[:4]

    return render(request, "ShopperMartapp/product_detail.html", {
        "product": product,
        "related_products": related_products
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
        # subtotal is a property in the model, no need to calculate/assign it here
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

        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create Order
            order = Order.objects.create(
                user=request.user,
                total=0,
                full_name=form.cleaned_data["full_name"],
                email=form.cleaned_data["email"],
                address=form.cleaned_data["address"],
                city=form.cleaned_data["city"],
                postal_code=form.cleaned_data["postal_code"],
                payment=dict(form.fields['payment_method'].choices)[form.cleaned_data["payment_method"]] # Store label
            )
            
            # Check stock first
            for item in cart_items:
                if item.quantity > item.product.stock:
                    messages.error(request, f"Not enough stock for {item.product.name}. Only {item.product.stock} left.")
                    order.delete() # rollback
                    return redirect("cart")

            for item in cart_items:
                # Decrement stock
                product = item.product
                product.stock -= item.quantity
                product.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.price,
                )
            
            order.total = total
            order.save()

            # Clear cart
            cart.items.all().delete()
            messages.success(request, f"Order placed successfully! Order ID: {order.id}")
            return redirect("my_orders")
    else:
        # Pre-fill form with profile data
        initial_data = {
            "full_name": request.user.profile.full_name,
            "email": request.user.email,
            "address": f"{request.user.profile.address_line1} {request.user.profile.address_line2}",
            "city": request.user.profile.city,
            "postal_code": request.user.profile.pincode
        }
        form = CheckoutForm(initial=initial_data)

    return render(request, "ShopperMartapp/checkout.html", {
        "cart_items": cart_items,
        "total": total,
        "form": form
    })


@login_required
def my_orders(request):
    """Display a list of orders for the logged-in user."""
    orders = Order.objects.filter(user=request.user).order_by("-created_at").prefetch_related("items__product")
    return render(request, "ShopperMartapp/my_orders.html", {"orders": orders})


@login_required
def cancel_order(request, order_id):
    """Cancel an order and restore stock."""
    order = get_object_or_404(Order, user=request.user, id=order_id)
    
    # Restore stock
    for item in order.items.all():
        if item.product:
            item.product.stock += item.quantity
            item.product.save()
            
    order.delete()
    messages.success(request, f"Order #{order_id} has been cancelled.")
    return redirect("my_orders")


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
