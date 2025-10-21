from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

def role_required(role: str):
    def deco(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if getattr(request.user, "role", None) == role:
                return view_func(request, *args, **kwargs)
            # raise PermissionDenied  # Optionally, redirect to a "not allowed" page
            return redirect("not_allowed")
        return _wrapped
    return deco
