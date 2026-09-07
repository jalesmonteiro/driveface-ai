from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(exc, PermissionDenied):
            code = getattr(exc, "code", "permission_denied")
            if hasattr(exc.detail, "code"):
                code = exc.detail.code
            response.data = {
                "error_code": str(code).upper() if code else "ACL_FORBIDDEN",
                "detail": str(exc.detail),
            }

    return response
