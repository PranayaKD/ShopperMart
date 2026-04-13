/**
 * ShopperMart | Unbreakable Cart Sync Manager
 * Handles offline persistence and auto-recovery for shopping actions.
 */

class CartSyncManager {
    constructor() {
        this.queueKey = 'shoppermart_sync_queue';
        this.init();
    }

    init() {
        // 1. Listen for clicks on Add-to-Cart buttons
        document.addEventListener('click', (e) => this.handleCartAction(e));

        // 2. Listen for online status to flush queue
        window.addEventListener('online', () => this.flushQueue());

        // 3. Initial flush on load
        this.flushQueue();

        console.log("CartSync: Initialized.");
    }

    getQueue() {
        return JSON.parse(localStorage.getItem(this.queueKey) || '[]');
    }

    saveQueue(queue) {
        localStorage.setItem(this.queueKey, JSON.stringify(queue));
    }

    async handleCartAction(e) {
        const btn = e.target.closest('.js-add-to-cart-btn');
        if (!btn) return;

        const productId = btn.dataset.productId;
        const form = btn.closest('form');
        const quantityInput = form ? form.querySelector('input[name="quantity"]') : null;
        const quantity = quantityInput ? parseInt(quantityInput.value) : 1;

        // If offline, we intercept and save
        if (!navigator.onLine) {
            e.preventDefault();
            this.addToQueue(productId, quantity, btn.dataset.productName);
            this.showToast(`Offline: ${btn.dataset.productName} will be added once connection is restored.`, 'info');
        } else {
            // Even if online, we record the intent briefly in case the request fails mid-way
            this.addToQueue(productId, quantity, btn.dataset.productName);
            // We let the form submit naturally (or AJAX)
            // But we'll remove it from queue if we reach a new page or get a success response
        }
    }

    addToQueue(productId, quantity, name) {
        let queue = this.getQueue();
        // Check if already in queue to avoid duplicates
        const existing = queue.find(item => item.id === productId);
        if (existing) {
            existing.qty += quantity;
        } else {
            queue.push({ id: productId, qty: quantity, name: name, timestamp: Date.now() });
        }
        this.saveQueue(queue);
    }

    async flushQueue() {
        if (!navigator.onLine) return;

        let queue = this.getQueue();
        if (queue.length === 0) return;

        console.log(`CartSync: Attempting to sync ${queue.length} items...`);

        for (const item of [...queue]) {
            try {
                const success = await this.syncItemToServer(item);
                if (success) {
                    // Remove from queue
                    queue = queue.filter(i => i.id !== item.id);
                    this.saveQueue(queue);
                    this.showToast(`Restored: ${item.name} successfully added to your cart.`, 'success');
                }
            } catch (err) {
                console.error("CartSync: Sync failed for item", item.id, err);
            }
        }
    }

    async syncItemToServer(item) {
        // We use the JSON API endpoint for syncing
        const response = await fetch('/api/cart/add/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify({
                product_id: item.id,
                quantity: item.qty
            })
        });

        return response.ok;
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast-item pointer-events-auto bg-black/90 backdrop-blur-xl text-white px-8 py-5 rounded-2xl shadow-2xl border border-white/10 flex items-center gap-6 min-w-[320px] transition-all duration-700 transform translate-x-full opacity-0`;
        
        const iconColor = type === 'success' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400';
        const icon = type === 'success' ? 'check_circle' : 'sync';

        toast.innerHTML = `
            <div class="w-10 h-10 rounded-full flex items-center justify-center ${iconColor}">
              <span class="material-symbols-outlined text-[20px]">${icon}</span>
            </div>
            <div class="flex flex-col w-full">
              <div class="flex items-center justify-between mb-2">
                <span class="font-mono text-[9px] uppercase tracking-widest opacity-40 font-bold">Network Recovery</span>
              </div>
              <p class="font-serif text-[13px] tracking-tight">${message}</p>
            </div>
        `;

        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.remove('translate-x-full', 'opacity-0');
            toast.classList.add('translate-x-0', 'opacity-100');
        }, 100);

        setTimeout(() => {
            toast.classList.add('translate-x-full', 'opacity-0');
            setTimeout(() => toast.remove(), 1000);
        }, 5000);
    }
}

// Global Clearer: If the user manually navigates to the cart, 
// we assume the server is truth and we can clear the local intent queue.
if (window.location.pathname.includes('/cart/')) {
    localStorage.setItem('shoppermart_sync_queue', '[]');
}

window.cartSync = new CartSyncManager();
