from django import template
from decimal import Decimal
register = template.Library()

@register.filter
def brl(value):
    try:
        v = Decimal(str(value))
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

@register.filter
def lucro_class(value):
    try:
        return 'lpos' if Decimal(str(value)) >= 0 else 'lneg'
    except:
        return ''

@register.filter
def pct(value, total):
    try:
        return int(float(value) / float(total) * 100)
    except:
        return 0

@register.filter
def format_km(value):
    try:
        return f"{int(value):,}".replace(",", ".") + " km"
    except:
        return "-"

@register.filter
def split_checklist(value):
    if not value:
        return []
    return [v.strip() for v in value.split(';') if v.strip()]
