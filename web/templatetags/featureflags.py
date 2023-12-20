from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def enable_xp_reservation():
    return getattr(settings, "ENABLE_XP_RESERVATION", "")


@register.simple_tag
def enable_xp_vege():
    return getattr(settings, "ENABLE_XP_VEGE", "")


@register.simple_tag
def enable_partners():
    return getattr(settings, "ENABLE_PARTNERS", "")


@register.simple_tag
def enable_teledeclaration():
    return getattr(settings, "ENABLE_TELEDECLARATION", "")


@register.simple_tag
def teledeclaration_end_date():
    return getattr(settings, "TELEDECLARATION_END_DATE", "")


@register.simple_tag
def enable_dashboard():
    return getattr(settings, "ENABLE_DASHBOARD", "")


@register.simple_tag
def enable_import_v2():
    return getattr(settings, "ENABLE_IMPORT_V2", "")
