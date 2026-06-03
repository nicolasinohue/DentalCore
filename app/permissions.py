from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


ROLE_ADMIN = "Administrador"
ROLE_DENTIST = "Dentista"
ROLE_RECEPTION = "Recepcao"


def has_role(user, *roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if has_role(request.user, *roles):
                return view_func(request, *args, **kwargs)
            messages.error(request, "Voce nao tem permissao para acessar esta area.")
            return redirect("dashboard")

        return wrapper

    return decorator
