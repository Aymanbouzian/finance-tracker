from django.conf import settings


def currency(request):
    return {"CURRENCY": settings.CURRENCY}
