from django.conf import settings


def registration_settings(request):
    return {
        "allow_public_registration": settings.ALLOW_PUBLIC_REGISTRATION,
    }
