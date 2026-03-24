from django import template

register = template.Library()

COUNTRY_ABBR = {
    "United States of America": "USA",
    "United Kingdom": "UK",
}


@register.filter
def country_abbr(name):
    return COUNTRY_ABBR.get(name, name)
