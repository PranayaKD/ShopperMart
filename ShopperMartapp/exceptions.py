import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler to prevent leaking internal traces in 500 errors
    while standardizing API error responses across DRF endpoints.
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Format DRF standard errors cleanly
        if isinstance(response.data, dict) and "detail" in response.data:
            response.data = {
                "success": False,
                "error": response.data.get("detail"),
                "status_code": response.status_code,
            }
        elif isinstance(response.data, dict):
            response.data = {
                "success": False,
                "errors": response.data,
                "status_code": response.status_code,
            }
        return response

    # Unhandled server exception (500)
    view_name = context.get("view", None)
    logger.error(f"Unhandled 500 API Exception in {view_name}: {exc}", exc_info=True)

    return Response(
        {
            "success": False,
            "error": "InternalServerError",
            "message": "An unexpected server error occurred. Please try again later.",
            "status_code": 500,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

