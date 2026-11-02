# ShopperMart Security Audit Report
> **Auditor**: Antigravity Security Agent (Powered by Cloudflare Security Audit Skill)  
> **Target**: `ShopperMart-main` (`c:\Users\dashp\dj1\ShopperMart-main`)  
> **Date**: October 30, 2026  
> **Status**: **All Code-Level Security Vulnerabilities Resolved & Patched**  
> **Scope**: Source-grounded comprehensive code review covering Authentication, Authorization, Payment Integrity, Session Lifecycle, Data Isolation, Input Validation, and Cloudflare/Web Security.

---

## 1. Executive Summary

A comprehensive, source-level security audit of the **ShopperMart** e-commerce application was conducted following the six-phase methodology of the **Cloudflare Security Audit Skill** (`cloudflare/security-audit-skill`).

### Resolution Summary:
- **Finding 1 [CRITICAL] Payment Amount Tampering**: **RESOLVED** — Strict server-side database derivation enforced; client-side price tampering blocked.
- **Finding 2 [HIGH] IDOR in Payment Verification**: **RESOLVED** — Ownership verification against `request.user` / session token and gateway amount verification implemented.
- **Finding 3 [HIGH] Authentication Bypass via Mock Google OAuth**: **RESOLVED** — Restricted strictly to local developer testing (`DEBUG=True`); hard-blocked in production.
- **Finding 4 [HIGH] CSRF Vulnerability on Order Cancellation**: **RESOLVED** — Enforced `@require_POST` with CSRF protection on `cancel_order`.
- **Finding 5 [MEDIUM] Unvalidated Open Redirect**: **RESOLVED** — Validated via Django's `url_has_allowed_host_and_scheme`.
- **Finding 6 [MEDIUM] CSRF on Cart Add API**: **RESOLVED** — Removed `@csrf_exempt`; now fully protected by Django CSRF token middleware.
- **Finding 7 [LOW] DOM XSS in Search Highlighting**: **RESOLVED** — Sanitized via entity encoding `escapeHtml()`.

---

## 2. Threat Model & Trust Boundaries

```
[ Unauthenticated Client / Attacker ]
           │
           ▼
[ Public Surfaces: Search, Catalog, Cart Add, Google Auth Dispatcher ]
           │
           ▼ (Boundary 1: Authentication & Session)
[ Customer Surfaces: Cart, Checkout, Order Creation, Address Management ]
           │
           ▼ (Boundary 2: Payment Gateway & Signature Integrity)
[ Third-Party Services: Razorpay Orders / Webhook, Cloudinary CDN, Google Maps ]
           │
           ▼ (Boundary 3: Administrative & Staff Privilege)
[ Admin Surfaces: Django Admin, Stock Updates, Order Status Transitions ]
```

---

## 3. Patched Vulnerabilities & Security Fixes

### Finding 1: [CRITICAL] Arbitrary Payment Amount Tampering in Razorpay Order Creation
- **File**: `ShopperMartapp/views/payments.py` (Lines 48–75)
- **Attack Class**: Parameter Tampering / Insecure Business Logic
- **Status**: **RESOLVED**
- **Fix Implemented**:
  When `custom_order_id` is supplied, the payment amount is strictly queried from `Order.objects.get(id=custom_order_id).total * 100`. Client-supplied amounts are ignored and cannot override database values. User ownership of the order is verified before creating gateway orders.

---

### Finding 2: [HIGH] Insecure Direct Object Reference (IDOR) in Payment Verification
- **File**: `ShopperMartapp/views/payments.py` (Lines 155–190)
- **Attack Class**: Broken Object-Level Authorization (IDOR)
- **Status**: **RESOLVED**
- **Fix Implemented**:
  Order lookup is now verified against `request.user` (or the guest session ID for guest checkouts). In addition, the payment amount captured by Razorpay is fetched via API and compared against the order total before finalization.

---

### Finding 3: [HIGH] Authentication Bypass via Mock Google OAuth Dispatcher
- **File**: `ShopperMartapp/views/account.py` (Lines 22–35)
- **Attack Class**: Authentication Bypass / Insecure Fallback
- **Status**: **RESOLVED**
- **Fix Implemented**:
  Demo test login is wrapped in an explicit `if not settings.DEBUG:` gate. In production, unconfigured OAuth immediately redirects to the standard login page with an error message. In development (`DEBUG=True`), testing continues seamlessly.

---

### Finding 4: [HIGH] CSRF Vulnerability on Order Cancellation
- **File**: `ShopperMartapp/views/orders.py` (Lines 378–385)
- **Attack Class**: Cross-Site Request Forgery (CSRF)
- **Status**: **RESOLVED**
- **Fix Implemented**:
  Added `@require_POST` decorator alongside `@login_required` and `@transaction.atomic`. GET-based cancellation via embedded `<img>` tags or malicious links is blocked with HTTP 405 Method Not Allowed.

---

### Finding 5: [MEDIUM] Unvalidated Open Redirect in Auth Dispatcher
- **File**: `ShopperMartapp/views/account.py` (Lines 55–65)
- **Attack Class**: CWE-601: Open Redirect
- **Status**: **RESOLVED**
- **Fix Implemented**:
  `next_url` is validated using Django's `url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})`. Any unauthorized off-site redirect safely defaults to the internal `'profile'` route.

---

### Finding 6: [MEDIUM] Cross-Site Request Forgery on Cart Add API
- **File**: `ShopperMartapp/views/cart.py` (Lines 167–172)
- **Attack Class**: CSRF Protection Bypass
- **Status**: **RESOLVED**
- **Fix Implemented**:
  Removed `@csrf_exempt`. The view now enforces Django's standard CSRF token validation, matching the `X-CSRFToken` header sent by `quickAddToCart`.

---

### Finding 7: [LOW] DOM XSS via Autocomplete Highlighting
- **File**: `templates/base.html` (Lines 1667–1675)
- **Status**: **RESOLVED**
- **Fix Implemented**:
  Added `escapeHtml()` sanitizer ensuring all search results and titles are entity-encoded before dynamic regex highlighting and DOM insertion.

---

## 4. Future Production Deployment Checklist (For When You Go Live)

These items are for when your project moves from development to production hosting:

1. **`DEBUG` Flag**:
   - Set `DEBUG=False` in production `.env`.
2. **`SECRET_KEY`**:
   - Generate a 50+ character random alphanumeric secret key for your cloud production deployment.
3. **Google Maps API Key**:
   - In Google Cloud Console, restrict your API key's HTTP referrers to your live production domain (`*.onrender.com/*`).
4. **Cloudinary API Credentials**:
   - Credentials are stored in `.env` and kept strictly out of version control.
