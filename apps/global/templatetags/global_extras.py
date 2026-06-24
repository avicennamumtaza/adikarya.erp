from django import template

register = template.Library()

@register.filter
def splitlines(value):
    """Split a string by newlines, returning a list of non-empty lines."""
    if not value:
        return []
    return [line for line in value.split('\n') if line.strip()]
