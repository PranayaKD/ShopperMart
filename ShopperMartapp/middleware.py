
class PreLoginSessionMiddleware:
    """
    Captures the anonymous session key before it is flushed during login.
    This allows signal receivers (like cart merging) to access the original 
    shopping cart even after the session has been rotated.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We only care about the session key if the user is not yet authenticated
        # and has a session. If they are about to log in, this key will be 
        # rotated, so we store it in a temporary request attribute.
        if not request.user.is_authenticated:
            request.pre_login_session_key = request.session.session_key
        else:
            request.pre_login_session_key = None
            
        response = self.get_response(request)
        return response
