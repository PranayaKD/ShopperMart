# ShopperMartapp/admin.py
from django.contrib import admin
from .models import Product, Category, Profile, Review, OrderStatusLog
from .models import Order, OrderItem


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "phone", "city", "state")
    search_fields = ("user__username", "full_name", "phone")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "available", "low_stock")
    list_filter = ("available", "category")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(boolean=True, description="Low Stock?")
    def low_stock(self, obj):
        return obj.low_stock


# ── Review Admin (with Approval Workflow) ──
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    list_editable = ("is_approved",)
    search_fields = ("product__name", "user__username", "comment")
    actions = ["approve_reviews", "reject_reviews"]

    @admin.action(description="✅ Approve selected reviews")
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} review(s) approved.")

    @admin.action(description="❌ Reject selected reviews")
    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} review(s) rejected.")


# ── Order Admin (with Status Log Audit Trail) ──
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderStatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "note", "created_at")
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "total", "status", "created_at")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    inlines = [OrderItemInline, OrderStatusLogInline]

    def save_model(self, request, obj, form, change):
        """Log status changes automatically when admin updates an order."""
        if change and 'status' in form.changed_data:
            old_status = form.initial.get('status', '')
            OrderStatusLog.objects.create(
                order=obj,
                old_status=old_status,
                new_status=obj.status,
                changed_by=request.user,
                note=f"Status changed via admin panel by {request.user.username}"
            )
        super().save_model(request, obj, form, change)

admin.site.register(OrderItem)