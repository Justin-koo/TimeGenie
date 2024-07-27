from django import template
register = template.Library()

@register.filter
def group_sections_by_course(sections):
    result = {}
    for section in sections:
        if section.course in result:
            result[section.course].append(section.section_code)
        else:
            result[section.course] = [section.section_code]
    return result.items()

@register.filter
def get_item(dictionary, key):
    """Retrieve an item from a dictionary or list by key/index."""
    return dictionary.get(key) if isinstance(dictionary, dict) else dictionary[int(key)]

@register.filter
def in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()