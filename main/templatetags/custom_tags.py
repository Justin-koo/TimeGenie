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
