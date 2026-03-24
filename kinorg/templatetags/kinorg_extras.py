from django import template

register = template.Library()

COUNTRY_ABBR = {
    "United States of America": "USA",
    "United Kingdom": "UK",
}

KEY_CREW_JOBS = {
    "Director", "Co-Director",
    "Writer", "Screenplay", "Original Screenplay", "Story", "Novel", "Adaptation", "Script",
    "Producer", "Executive Producer", "Co-Producer",
    "Director of Photography", "Cinematography",
    "Editor", "Film Editing",
    "Original Music Composer", "Music", "Composer",
    "Production Design", "Production Designer",
    "Costume Design", "Costume Designer",
    "Visual Effects Supervisor",
    "Casting",
}


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
        if member.get("job") in KEY_CREW_JOBS:
            key = (member["id"], member["job"])
            if key not in seen:
                seen.add(key)
                result.append(member)
    return result
