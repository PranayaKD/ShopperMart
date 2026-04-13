import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from ..models import Product, Category, Order, Review, User, Profile
from ..forms import ProductForm

logger = logging.getLogger(__name__)

# -------------------- DASHBOARD HUB --------------------
@staff_member_required
def admin_dashboard(request):
    """Business Intelligence Overview for ShopperMart Admins."""
    # 1. Sales Metrics
    total_revenue = Order.objects.filter(status='delivered').aggregate(total=Sum('total'))['total'] or 0
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    shipping_orders = Order.objects.filter(status='shipped').count()
    
    # 2. Feedback Metrics
    pending_reviews = Review.objects.filter(is_approved=False).count()
    
    # 3. Inventory Metrics
    low_stock_products = Product.objects.filter(stock__lte=5, is_deleted=False).count()
    total_products = Product.objects.filter(is_deleted=False).count()

    # 4. Customer Metrics
    total_customers = User.objects.filter(is_staff=False).count()
    
    # Recent Activities (Orders)
    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    
    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'shipping_orders': shipping_orders,
        'pending_reviews': pending_reviews,
        'low_stock_products': low_stock_products,
        'total_products': total_products,
        'total_customers': total_customers,
        'recent_orders': recent_orders,
        'active_tab': 'dashboard'
    }
    return render(request, "administrator/dashboard.html", context)


# -------------------- PRODUCT MANAGEMENT (CRUD) --------------------
@staff_member_required
def admin_product_list(request):
    """Modern inventory management with search and filters."""
    query = request.GET.get('q', '')
    cat_slug = request.GET.get('category', '')
    
    products = Product.objects.filter(is_deleted=False).select_related('category')
    
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if cat_slug:
        products = products.filter(category__slug=cat_slug)
        
    context = {
        'products': products.order_by('-created_at'),
        'categories': Category.objects.all(),
        'query': query,
        'active_tab': 'products'
    }
    return render(request, "administrator/inventory.html", context)


@staff_member_required
def admin_product_upsert(request, pk=None):
    """Create or Edit products with a beautiful form."""
    product = get_object_or_404(Product, pk=pk) if pk else None
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            saved_product = form.save()
            messages.success(request, f"Product '{saved_product.name}' has been {'updated' if product else 'created'}.")
            return redirect('admin_product_list')
    else:
        form = ProductForm(instance=product)
        
    return render(request, "administrator/product_form.html", {
        'form': form,
        'product': product,
        'active_tab': 'products'
    })


@staff_member_required
def admin_product_delete(request, pk):
    """Soft-delete product with confirmation."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.is_deleted = True
        product.save()
        messages.success(request, f"Product '{product.name}' has been archived.")
        return redirect('admin_product_list')
    return render(request, "administrator/product_confirm_delete.html", {'product': product})


# -------------------- ORDER MANAGEMENT --------------------
@staff_member_required
def admin_order_list(request):
    """Track and manage order fulfillment."""
    status_filter = request.GET.get('status', '')
    orders = Order.objects.all()
    
    if status_filter:
        orders = orders.filter(status=status_filter)
        
    context = {
        'orders': orders,
        'active_tab': 'orders',
        'status_filter': status_filter
    }
    return render(request, "administrator/orders.html", context)


@staff_member_required
def admin_order_detail(request, order_id):
    """Handle fulfillment and status transitions for a specific order."""
    order = get_object_or_404(Order, pk=order_id)
    
    if request.method == "POST":
        new_status = request.POST.get('status')
        note = request.POST.get('note', '')
        try:
            order.change_status(new_status, user=request.user, note=note)
            messages.success(request, f"Order status updated to {new_status.replace('_', ' ').title()}.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('admin_order_detail', order_id=order.id)
        
    return render(request, "administrator/order_detail.html", {
        'order': order,
        'active_tab': 'orders'
    })


# -------------------- MODERATION --------------------
@staff_member_required
def admin_review_list(request):
    """Moderation queue for product reviews."""
    reviews = Review.objects.all().select_related('product', 'user').order_by('-created_at')
    
    if request.method == "POST":
        review_id = request.POST.get('review_id')
        action = request.POST.get('action') # 'approve' or 'reject'
        review = get_object_or_404(Review, pk=review_id)
        
        if action == 'approve':
            review.is_approved = True
            review.save()
            messages.success(request, "Review approved.")
        elif action == 'reject':
            review.is_approved = False
            review.save()
            messages.info(request, "Review rejected.")
        return redirect('admin_review_list')

    context = {
        'reviews': reviews,
        'active_tab': 'reviews'
    }
    return render(request, "administrator/moderation.html", context)
