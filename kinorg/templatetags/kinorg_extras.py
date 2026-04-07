import json
from django import template

register = template.Library()

COUNTRY_ABBR = {
    "United States of America": "USA",
    "United Kingdom": "UK",
}

KEY_CREW_JOBS = {
    "Director", "Co-Director",
    "Writer", "Screenplay", "Original Screenplay", "Story", "Novel", "Adaptation", "Script",
    "Producer",
    "Director of Photography", "Cinematography",
    "Editor", "Film Editing",
    "Original Music Composer", "Music", "Composer",
    "Production Design", "Production Designer",
    "Costume Design", "Costume Designer",
    "Visual Effects Supervisor",
    "Casting",
}

# Lower index = shown first
JOB_PRIORITY = [
    "Director", "Co-Director",
    "Writer", "Screenplay", "Original Screenplay", "Story", "Novel", "Adaptation", "Script",
    "Director of Photography", "Cinematography",
    "Editor", "Film Editing",
    "Original Music Composer", "Music", "Composer",
    "Production Design", "Production Designer",
    "Costume Design", "Costume Designer",
    "Producer",
    "Visual Effects Supervisor",
    "Casting",
]


@register.filter
def film_director(crew_list):
    """Return first Director name from a crew JSONField list, or empty string."""
    if not crew_list:
        return ''
    if isinstance(crew_list, str):
        try:
            crew_list = json.loads(crew_list)
        except (ValueError, TypeError):
            return ''
    for member in crew_list:
        if isinstance(member, dict) and member.get('job') == 'Director':
            return member.get('name', '')
    return ''


@register.filter
def country_abbr(name):
    return COUNTRY_ABBR.get(name, name)


@register.filter
def key_crew(crew_list):
    if not crew_list:
        return []
    seen = set()
    result = []
    for member in crew_list:
        if member.get("job") in KEY_CREW_JOBS and member.get("id"):
            key = (member["id"], member["job"])
            if key not in seen:
                seen.add(key)
                result.append(member)
    result.sort(key=lambda m: JOB_PRIORITY.index(m["job"]) if m["job"] in JOB_PRIORITY else 99)
    return result
