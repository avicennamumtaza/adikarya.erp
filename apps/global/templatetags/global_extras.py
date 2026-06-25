import re
from django import template

register = template.Library()

@register.filter
def splitlines(value):
    """Split a string by newlines, returning a list of non-empty lines."""
    if not value:
        return []
    return [line for line in value.split('\n') if line.strip()]

@register.filter
def wa_url(value):
    """Convert a WhatsApp number to a WhatsApp chat URL."""
    if not value:
        return ''
    digits = re.sub(r'\D', '', str(value))
    if not digits:
        return ''
    if digits.startswith('0'):
        digits = '62' + digits[1:]
    elif not digits.startswith('62'):
        digits = '62' + digits
    return f'https://wa.me/{digits}'
