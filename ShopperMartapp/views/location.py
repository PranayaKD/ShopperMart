import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def delivery_location(request):
    """
    GET: Retrieve the active delivery location from session or authenticated user's profile.
    POST: Store chosen delivery location (address, locality, city, state, postal_code, lat, lng)
          into the session and sync with User Profile if authenticated.
    """
    if request.method == "POST":
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = request.POST.dict()

            location_payload = {
                "address": data.get("address", "").strip(),
                "locality": data.get("locality", "").strip() or data.get("city", "").strip(),
                "city": data.get("city", "").strip(),
                "state": data.get("state", "").strip(),
                "postal_code": data.get("postal_code", "").strip() or data.get("pincode", "").strip(),
                "landmark": data.get("landmark", "").strip(),
                "latitude": data.get("latitude") or data.get("lat"),
                "longitude": data.get("longitude") or data.get("lng"),
            }

            request.session["delivery_location"] = location_payload
            request.session.modified = True

            # If logged in, optionally save to Profile
            if request.user.is_authenticated:
                profile = getattr(request.user, "profile", None)
                if profile:
                    if location_payload["address"]:
                        profile.address_line1 = location_payload["address"]
                    if location_payload["city"]:
                        profile.city = location_payload["city"]
                    if location_payload["state"]:
                        profile.state = location_payload["state"]
                    if location_payload["postal_code"]:
                        profile.pincode = location_payload["postal_code"]
                    profile.save()

            return JsonResponse({
                "success": True,
                "message": "Delivery location set for 10-minute order dispatch.",
                "location": location_payload
            })

        except Exception as e:
            logger.error(f"Error setting delivery location: {e}", exc_info=True)
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    # GET
    location = request.session.get("delivery_location")
    if not location and request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and profile.pincode:
            location = {
                "address": profile.address_line1 or "",
                "locality": profile.city or "",
                "city": profile.city or "",
                "state": profile.state or "",
                "postal_code": profile.pincode or "",
                "landmark": profile.landmark or "",
                "latitude": None,
                "longitude": None,
            }
            request.session["delivery_location"] = location

    return JsonResponse({
        "success": True,
        "location": location or {
            "locality": "Bhadrak Sector 4",
            "postal_code": "756100",
            "city": "Bhadrak",
            "state": "Odisha",
            "address": "Bhadrak Sector 4, Odisha, 756100"
        }
    })
