from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """Adds a CSS class to a form field."""
    return value.as_widget(attrs={'class': arg})

@register.filter(name='replace')
def replace(value, arg):
    """Replaces characters in a string. Usage: {{ val|replace:"search,replace" }}"""
    if ',' not in arg:
        return value
    search, replace_with = arg.split(',')
    return value.replace(search, replace_with)

@register.filter(name='div')
def div(value, arg):
    """Simple division filter."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter(name='mul')
def mul(value, arg):
    """Simple multiplication filter."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='split')
def split(value, arg):
    """Splits a string by a delimiter."""
    return value.split(arg)
