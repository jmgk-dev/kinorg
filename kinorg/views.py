import functools
import operator
import os
import re
import json
from datetime import date as _date
from urllib.parse import quote

import requests

from django.shortcuts import render, redirect
from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.db import connection
from django.db.models.fields.json import KeyTransform
from django.db.models.functions import Cast
from django.db.models import IntegerField, F, Q

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.urls import reverse_lazy

from django.core.cache import cache

from .models import Film, FilmList, Addition, Invitation, WatchedFilm, PCCScreening, LikedFilm
from better_profanity import profanity


COUNTRY_ISO = {
    # Major English-speaking
    'US': 'USA', 'GB': 'UK', 'AU': 'Australia', 'CA': 'Canada',
    'NZ': 'New Zealand', 'IE': 'Ireland',
    # Europe
    'FR': 'France', 'DE': 'Germany', 'IT': 'Italy', 'ES': 'Spain',
    'PT': 'Portugal', 'NL': 'Netherlands', 'BE': 'Belgium', 'CH': 'Switzerland',
    'AT': 'Austria', 'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark',
    'FI': 'Finland', 'PL': 'Poland', 'CZ': 'Czech Republic', 'SK': 'Slovakia',
    'HU': 'Hungary', 'RO': 'Romania', 'BG': 'Bulgaria', 'GR': 'Greece',
    'HR': 'Croatia', 'SI': 'Slovenia', 'RS': 'Serbia', 'BA': 'Bosnia and Herzegovina',
    'ME': 'Montenegro', 'MK': 'North Macedonia', 'AL': 'Albania', 'XK': 'Kosovo',
    'LT': 'Lithuania', 'LV': 'Latvia', 'EE': 'Estonia', 'IS': 'Iceland',
    'LU': 'Luxembourg', 'MT': 'Malta', 'CY': 'Cyprus', 'LI': 'Liechtenstein',
    # Eastern Europe / former USSR
    'RU': 'Russia', 'UA': 'Ukraine', 'BY': 'Belarus', 'MD': 'Moldova',
    'GE': 'Georgia', 'AM': 'Armenia', 'AZ': 'Azerbaijan',
    'KZ': 'Kazakhstan', 'UZ': 'Uzbekistan',
    # Historical
    'SU': 'Soviet Union', 'YU': 'Yugoslavia', 'CS': 'Czechoslovakia', 'XC': 'Czechoslovakia', 'DD': 'East Germany',
    # Middle East
    'IL': 'Israel', 'IR': 'Iran', 'IQ': 'Iraq', 'SY': 'Syria',
    'LB': 'Lebanon', 'JO': 'Jordan', 'TR': 'Turkey',
    'SA': 'Saudi Arabia', 'AE': 'UAE', 'QA': 'Qatar', 'KW': 'Kuwait',
    # Asia
    'JP': 'Japan', 'KR': 'South Korea', 'CN': 'China', 'HK': 'Hong Kong',
    'TW': 'Taiwan', 'IN': 'India', 'TH': 'Thailand', 'VN': 'Vietnam',
    'KH': 'Cambodia', 'PH': 'Philippines', 'ID': 'Indonesia', 'MY': 'Malaysia',
    'SG': 'Singapore', 'MM': 'Myanmar', 'MN': 'Mongolia',
    'PK': 'Pakistan', 'BD': 'Bangladesh', 'LK': 'Sri Lanka', 'NP': 'Nepal',
    # Africa
    'ZA': 'South Africa', 'NG': 'Nigeria', 'EG': 'Egypt', 'MA': 'Morocco',
    'TN': 'Tunisia', 'DZ': 'Algeria', 'KE': 'Kenya', 'GH': 'Ghana',
    'SN': 'Senegal', 'CI': "Côte d'Ivoire", 'CM': 'Cameroon',
    'ET': 'Ethiopia', 'TZ': 'Tanzania', 'UG': 'Uganda',
    'AO': 'Angola', 'BF': 'Burkina Faso', 'CD': 'DR Congo',
    # Latin America
    'MX': 'Mexico', 'BR': 'Brazil', 'AR': 'Argentina', 'CL': 'Chile',
    'CO': 'Colombia', 'VE': 'Venezuela', 'PE': 'Peru', 'CU': 'Cuba',
    'UY': 'Uruguay', 'EC': 'Ecuador', 'BO': 'Bolivia', 'PY': 'Paraguay',
    'CR': 'Costa Rica', 'GT': 'Guatemala', 'PA': 'Panama',
    'DO': 'Dominican Republic', 'JM': 'Jamaica',
}


def _to_str_set(lst, key='name'):
    """Normalise a JSONField that may contain strings or dicts."""
    result = set()
    for item in (lst or []):
        if isinstance(item, str):
            result.add(item)
        elif isinstance(item, dict) and key in item:
            result.add(item[key])
    return result


def get_similar_films(film_id, film_obj, limit=12):
    """Score DB films by metadata similarity. Returns top `limit` Film objects."""
    if not film_obj:
        return []

    genres = _to_str_set(film_obj.genres)
    keywords = _to_str_set(film_obj.keywords)
    countries = _to_str_set(film_obj.production_countries, key='iso_3166_1')
    directors = {c['name'] for c in (film_obj.crew or []) if isinstance(c, dict) and c.get('job') == 'Director'}
    decade = (film_obj.release_date.year // 10) * 10 if film_obj.release_date else None

    candidates = Film.objects.exclude(id=film_id).filter(
        release_date__isnull=False, poster_path__gt=''
    )

    scored = []
    for f in candidates:
        score = len(genres & _to_str_set(f.genres)) * 3
        score += min(len(keywords & _to_str_set(f.keywords)), 5)
        score += len(countries & _to_str_set(f.production_countries, key='iso_3166_1')) * 2
        if directors & {c['name'] for c in (f.crew or []) if isinstance(c, dict) and c.get('job') == 'Director'}:
            score += 5
        if decade and f.release_date and (f.release_date.year // 10) * 10 == decade:
            score += 1
        if score > 0:
            scored.append((score, f))

    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored[:limit]]


# Functions ------------------------------------------------------------>

def get_tmdb_data(url):

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.environ.get('TMDB_KEY')}"
    }

    search_response = requests.get(url, headers=headers)
    search_data = search_response.json()

    return search_data


def order_by_popularity(search_results):
    # Movies first, then people, ordered by popularity within each group
    movies = sorted([r for r in search_results if r.get('media_type') == 'movie' or 'release_date' in r], 
                    key=lambda i: i['popularity'], reverse=True)
    people = sorted([r for r in search_results if r.get('media_type') == 'person'], 
                    key=lambda i: i['popularity'], reverse=True)
    return movies + people


def films_and_people(search_data):

    filtered_films = [film for film in search_data["results"] if film['media_type'] == 'movie' or film['media_type'] == 'person']

    return filtered_films


def send_invitation(invited_list, to_user, from_user):

    if from_user != invited_list.owner:
        raise PermissionError("You don't have permission!")

    elif to_user == invited_list.owner:
        raise PermissionError("You're already the owner!")

    elif Invitation.objects.filter(to_user=to_user, film_list=invited_list).exists():
        raise PermissionError("Already invited!")

    else:
        invitation, created = Invitation.objects.get_or_create(
            from_user=invited_list.owner,
            to_user=to_user,
            film_list=invited_list,
        )
        invitation.save()


def accept_invitation(invited_list, user):
    invitation = Invitation.objects.filter(
        film_list=invited_list,
        to_user=user,
        accepted=False
        ).first()
    if invitation:
        invitation.accepted=True
        invitation.save()
        invited_list.guests.add(user)


def decline_invitation(invited_list, user):
    invitation = Invitation.objects.filter(
        film_list=invited_list,
        to_user=user,
        accepted=False
        ).first()
    if invitation:
        invitation.declined=True
        invitation.save()


def film_autocomplete(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    filter_type = request.GET.get('filter', 'all')  # 'all', 'films', 'people'

    cache_key = f'tmdb_autocomplete_{query.replace(" ", "_")}_{filter_type}'
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse({'results': cached})

    # People whose English name isn't their TMDB primary name and won't appear in search
    PERSON_ALIASES = {
        'john woo': 11401,
    }

    # Parse year from query e.g. "stalker 1979"
    year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', query)
    year = year_match.group(1) if year_match else None
    clean_query = re.sub(r'\b(19\d{2}|20[0-2]\d)\b', '', query).strip() if year else query

    if year and filter_type != 'people':
        # Use search/movie with year for much better targeted results
        data = get_tmdb_data(
            f"https://api.themoviedb.org/3/search/movie?query={clean_query}&year={year}&include_adult=false&language=en-US&page=1"
        )
        raw = [dict(r, media_type='movie') for r in data.get('results', [])]
    else:
        data = get_tmdb_data(
            f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US&page=1"
        )
        raw = [r for r in data.get('results', []) if r.get('media_type') in ('movie', 'person')]

        # Also search people directly — search/multi can miss directors with low popularity
        if filter_type != 'films':
            person_data = get_tmdb_data(
                f"https://api.themoviedb.org/3/search/person?query={query}&include_adult=false&language=en-US&page=1"
            )
            existing_ids = {r['id'] for r in raw if r.get('media_type') == 'person'}
            for p in person_data.get('results', []):
                if p['id'] not in existing_ids:
                    raw.append(dict(p, media_type='person'))

    # Apply filter
    if filter_type == 'films':
        raw = [r for r in raw if r.get('media_type') == 'movie']
    elif filter_type == 'people':
        raw = [r for r in raw if r.get('media_type') == 'person']

    # Inject aliased people who can't be found via normal TMDB search
    if filter_type != 'films':
        alias_id = PERSON_ALIASES.get(clean_query.lower())
        if alias_id:
            already_present = any(r.get('id') == alias_id and r.get('media_type') == 'person' for r in raw)
            if not already_present:
                alias_data = get_tmdb_data(f"https://api.themoviedb.org/3/person/{alias_id}?language=en-US")
                if alias_data.get('id'):
                    credits = get_tmdb_data(f"https://api.themoviedb.org/3/person/{alias_id}/movie_credits?language=en-US")
                    top_films = sorted(credits.get('crew', []) + credits.get('cast', []),
                                       key=lambda f: -f.get('popularity', 0))
                    seen, known_for = set(), []
                    for f in top_films:
                        if f['id'] not in seen and f.get('title'):
                            seen.add(f['id'])
                            known_for.append({'title': f['title'], 'media_type': 'movie'})
                        if len(known_for) == 3:
                            break
                    alias_data['known_for'] = known_for
                    raw.insert(0, dict(alias_data, media_type='person', popularity=999))

    # Filter out people with no profile photo — low-data profiles give empty click-throughs
    raw = [r for r in raw if r.get('media_type') != 'person' or r.get('profile_path')]

    # Exact name/title matches first, people boosted, then by popularity
    query_lower = clean_query.lower()
    def sort_key(r):
        title = (r.get('title') or r.get('name') or '').lower()
        exact = title == query_lower
        is_person = r.get('media_type') == 'person'
        effective_pop = r.get('popularity', 0) * (3 if is_person else 1)
        return (not exact, -effective_pop)
    raw = sorted(raw, key=sort_key)

    LANG_TO_COUNTRY = {
        'fr': 'France', 'de': 'Germany', 'it': 'Italy', 'ja': 'Japan',
        'ko': 'South Korea', 'zh': 'China', 'es': 'Spain', 'pt': 'Portugal',
        'sv': 'Sweden', 'da': 'Denmark', 'nb': 'Norway', 'fi': 'Finland',
        'ru': 'Russia', 'pl': 'Poland', 'hu': 'Hungary', 'ro': 'Romania',
        'cs': 'Czech Republic', 'tr': 'Turkey', 'fa': 'Iran', 'hi': 'India',
        'th': 'Thailand', 'el': 'Greece', 'he': 'Israel', 'nl': 'Netherlands',
        'ar': 'Arabic', 'uk': 'Ukraine', 'sk': 'Slovakia',
    }

    results = []
    for r in raw[:10]:
        if r.get('media_type') == 'movie':
            codes = r.get('origin_country', [])
            if codes:
                country = COUNTRY_ISO.get(codes[0], codes[0])
            else:
                lang = r.get('original_language', '')
                country = LANG_TO_COUNTRY.get(lang, '')
            results.append({
                'id': r['id'],
                'title': r.get('title', ''),
                'year': r.get('release_date', '')[:4],
                'poster_path': r.get('poster_path') or '',
                'media_type': 'movie',
                'profile_path': '',
                'country': country,
            })
        elif r.get('media_type') == 'person':
            known_for_titles = [
                f.get('title') or f.get('name', '')
                for f in r.get('known_for', [])[:3]
                if f.get('title') or f.get('name')
            ]
            results.append({
                'id': r['id'],
                'title': r.get('name', ''),
                'year': '',
                'poster_path': '',
                'media_type': 'person',
                'profile_path': r.get('profile_path') or '',
                'known_for_department': r.get('known_for_department', ''),
                'known_for_titles': known_for_titles,
            })

    cache.set(cache_key, results, timeout=300)
    return JsonResponse({'results': results})


def user_autocomplete(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    list_id = request.GET.get('list_id')

    users = get_user_model()
    qs = users.objects.filter(
        username__icontains=query
    ).exclude(
        id=request.user.id
    )

    # Exclude already-invited users if list_id is provided
    if list_id:
        already_invited_ids = Invitation.objects.filter(
            film_list_id=list_id
        ).values_list('to_user_id', flat=True)
        qs = qs.exclude(id__in=already_invited_ids)

    results = qs.values('username')[:8]

    return JsonResponse({'results': list(results)})


# Functions END ------------------------------------------------------------>


class Home(ListView):

    model = Film
    template_name = "kinorg/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['has_lists'] = FilmList.objects.filter(owner=self.request.user).exists()
        return context


class About(TemplateView):

    template_name = "kinorg/about.html"


class Search(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/search.html"

    def get(self, request, *args, **kwargs):
        # Remove the redirect — blank search page is fine now
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('query', '').strip()
        context["query"] = query
        context["results_list"] = []
        context["collections"] = COLLECTIONS
        return context


class CreateList(LoginRequiredMixin, CreateView):

    login_url = "user_admin:login"

    model = FilmList
    fields = ["title"]
    template_name_suffix = "_create_form"
    success_url = reverse_lazy("kinorg:my_lists")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MyLists(LoginRequiredMixin, TemplateView):
    
    login_url = "user_admin:login"

    template_name = "kinorg/filmlist_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        my_lists = FilmList.objects.filter(owner=user).order_by('-id').prefetch_related('addition_set__film')
        guest_lists = FilmList.objects.filter(guests=user).order_by('-id')
        invitations = Invitation.objects.filter(to_user=user).exclude(accepted=True)

        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists
        context["invitations"] = invitations

        return context


SORT_MAP = {
    'date_desc': '-date_added',
    'date_asc': 'date_added',
    'title_asc': 'film__title',
    'title_desc': '-film__title',
    'release_desc': '-film__release_date',
    'release_asc': 'film__release_date',
}

COLLECTIONS = {
    'sight_and_sound_2022': 'Sight & Sound 2022 Poll',
    'tspdt_1000': "TSPDT 1000 Greatest Films",
    'tspdt_21c': "TSPDT 21st Century 1000",
    'criterion': 'Criterion Collection',
    'janus': 'Janus Films',
    'letterboxd_top_500': 'Letterboxd Top 500',
    'oscar_international_feature': 'Oscar International Feature',
    'vinegar_syndrome': 'Vinegar Syndrome',
}

RANKED_COLLECTIONS = {'tspdt_1000', 'tspdt_21c', 'sight_and_sound_2022', 'letterboxd_top_500'}

COLLECTION_SORT_MAP = {
    'title_asc': 'title',
    'title_desc': '-title',
    'release_desc': '-release_date',
    'release_asc': 'release_date',
}


def films_in_collection(tag):
    """Filter Films by collection tag, using the most efficient method for the current DB."""
    if connection.vendor == 'postgresql':
        return Film.objects.filter(collections__contains=[tag])
    return Film.objects.extra(where=["collections LIKE %s"], params=[f'%"{tag}"%'])


def _build_genre_list(qs):
    """Return sorted list of genre name strings from a Film queryset."""
    genres = set()
    for genres_val in qs.values_list('genres', flat=True):
        for g in (genres_val or []):
            if isinstance(g, dict) and g.get('name'):
                genres.add(g['name'])
    return sorted(genres)


def _filter_films_by_genre(qs, genre):
    """Filter a Film queryset by genre name, compatible with SQLite and PostgreSQL."""
    if connection.vendor == 'postgresql':
        return qs.filter(genres__contains=[{"name": genre}])
    return qs.extra(where=["genres LIKE %s"], params=[f'%"name": "{genre}"%'])


def _build_country_map(qs):
    """Return sorted list of (code, name) tuples from a Film queryset."""
    country_map = {}
    for film in qs.only('primary_country').exclude(primary_country=''):
        code = film.primary_country
        if code and code not in country_map:
            country_map[code] = COUNTRY_ISO.get(code, code)
    return sorted(country_map.items(), key=lambda x: x[1])


class ListDetail(LoginRequiredMixin, UserPassesTestMixin, DetailView):

    login_url = "user_admin:login"

    model = FilmList

    slug_field = 'sqid'

    def test_func(self):
        list_object = self.get_object()

        return list_object.owner == self.request.user or self.request.user in list_object.guests.all()

    def handle_no_permission(self):
        return redirect("kinorg:no_access")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        invitations = Invitation.objects.filter(
            film_list=self.get_object()
        ).select_related('to_user')

        sort = self.request.GET.get('sort', 'date_desc')
        country = self.request.GET.get('country', '')
        genre = self.request.GET.get('genre', '')

        additions = self.object.addition_set.select_related('film').order_by(
            SORT_MAP.get(sort, '-date_added')
        )

        if country:
            additions = additions.filter(film__primary_country=country)
        if genre:
            genre_film_ids = _filter_films_by_genre(Film.objects.all(), genre).values_list('id', flat=True)
            additions = additions.filter(film_id__in=genre_film_ids)

        # Build each filter list with the other filter applied, so they stay in sync
        all_films_qs = Film.objects.filter(addition__film_list=self.object)
        genres_qs = all_films_qs.filter(primary_country=country) if country else all_films_qs
        countries_qs = _filter_films_by_genre(all_films_qs, genre) if genre else all_films_qs
        genres = _build_genre_list(genres_qs)
        countries = _build_country_map(countries_qs)

        limit = 48
        total = additions.count()

        context['invitations'] = invitations
        context['additions'] = additions[:limit]
        context['has_more'] = total > limit
        context['next_offset'] = limit
        context['genres'] = genres
        context['countries'] = countries
        context['current_sort'] = sort
        context['current_country'] = country
        context['current_genre'] = genre

        return context


@login_required(login_url='user_admin:login')
def list_additions_json(request, slug):
    try:
        film_list = FilmList.objects.get(sqid=slug)
    except FilmList.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    if film_list.owner != request.user and request.user not in film_list.guests.all():
        return JsonResponse({'error': 'Forbidden'}, status=403)

    sort = request.GET.get('sort', 'date_desc')
    country = request.GET.get('country', '')
    genre = request.GET.get('genre', '')
    offset = int(request.GET.get('offset', 0))
    limit = 48

    additions = film_list.addition_set.select_related('film').order_by(
        SORT_MAP.get(sort, '-date_added')
    )

    if country:
        additions = additions.filter(film__primary_country=country)
    if genre:
        genre_film_ids = _filter_films_by_genre(Film.objects.all(), genre).values_list('id', flat=True)
        additions = additions.filter(film_id__in=genre_film_ids)

    total = additions.count()
    batch = additions[offset:offset + limit]

    films = [
        {
            'id': addition.film.id,
            'title': addition.film.title,
            'poster_path': addition.film.poster_path,
        }
        for addition in batch
    ]

    return JsonResponse({
        'films': films,
        'has_more': (offset + limit) < total,
        'next_offset': offset + limit,
    })


class CollectionDetail(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"
    template_name = "kinorg/collection_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag = self.kwargs['tag']

        if tag not in COLLECTIONS:
            raise Http404

        default_sort = 'rank' if tag in RANKED_COLLECTIONS else 'title_asc'
        sort = self.request.GET.get('sort', default_sort)
        country = self.request.GET.get('country', '')
        genre = self.request.GET.get('genre', '')

        base_qs = films_in_collection(tag)

        # Build each filter list with the other filter applied, so they stay in sync
        genres_qs = base_qs.filter(primary_country=country) if country else base_qs
        countries_qs = _filter_films_by_genre(base_qs, genre) if genre else base_qs
        genres = _build_genre_list(genres_qs)
        countries = _build_country_map(countries_qs)

        qs = base_qs.annotate(
            rank=Cast(KeyTransform(tag, 'collection_ranks'), IntegerField())
        )

        if country:
            qs = qs.filter(primary_country=country)
        if genre:
            qs = _filter_films_by_genre(qs, genre)

        if sort == 'rank':
            qs = qs.order_by(F('rank').asc(nulls_last=True))
        else:
            qs = qs.order_by(COLLECTION_SORT_MAP.get(sort, 'title'))

        limit = 48
        total = qs.count()

        context['tag'] = tag
        context['collection_name'] = COLLECTIONS[tag]
        context['collections'] = COLLECTIONS
        context['films'] = list(qs[:limit])
        context['total'] = total
        context['has_more'] = total > limit
        context['next_offset'] = limit
        context['genres'] = genres
        context['countries'] = countries
        context['current_sort'] = sort
        context['current_country'] = country
        context['current_genre'] = genre
        context['is_ranked'] = tag in RANKED_COLLECTIONS

        return context


@login_required(login_url='user_admin:login')
def collection_films_json(request, tag):
    if tag not in COLLECTIONS:
        return JsonResponse({'error': 'Not found'}, status=404)

    sort = request.GET.get('sort', 'rank')
    country = request.GET.get('country', '')
    genre = request.GET.get('genre', '')
    offset = int(request.GET.get('offset', 0))
    limit = 48

    qs = films_in_collection(tag).annotate(
        rank=Cast(KeyTransform(tag, 'collection_ranks'), IntegerField())
    )

    if country:
        qs = qs.filter(primary_country=country)
    if genre:
        qs = _filter_films_by_genre(qs, genre)

    if sort == 'rank':
        qs = qs.order_by(F('rank').asc(nulls_last=True))
    else:
        qs = qs.order_by(COLLECTION_SORT_MAP.get(sort, 'title'))

    total = qs.count()
    batch = list(qs[offset:offset + limit])

    films = [
        {
            'id': f.id,
            'title': f.title,
            'poster_path': f.poster_path,
            'rank': f.rank,
        }
        for f in batch
    ]

    return JsonResponse({
        'films': films,
        'has_more': (offset + limit) < total,
        'next_offset': offset + limit,
    })


PCC_PAGE_SIZE = 48


def _get_sorted_pcc_screenings(sort):
    """Return all non-hidden PCC screenings as sorted list of {screening, film} dicts."""
    screenings = list(
        PCCScreening.objects.filter(hidden=False).select_related('film').order_by('title')
    )
    unlinked = [s for s in screenings if s.film is None]
    if unlinked:
        q = functools.reduce(operator.or_, [Q(title__iexact=s.title) for s in unlinked])
        films_by_title = {f.title.lower(): f for f in Film.objects.filter(q)}
    else:
        films_by_title = {}

    matched = [
        {'screening': s, 'film': s.film or films_by_title.get(s.title.lower())}
        for s in screenings
    ]

    if sort == 'title_asc':
        matched.sort(key=lambda x: (x['film'].title if x['film'] else x['screening'].title).lower())
    elif sort == 'title_desc':
        matched.sort(key=lambda x: (x['film'].title if x['film'] else x['screening'].title).lower(), reverse=True)
    elif sort == 'release_desc':
        matched.sort(key=lambda x: x['film'].release_date if (x['film'] and x['film'].release_date) else _date.min, reverse=True)
    elif sort == 'release_asc':
        matched.sort(key=lambda x: x['film'].release_date if (x['film'] and x['film'].release_date) else _date.max)

    return matched


def _filter_pcc_matched(matched, country='', genre=''):
    """Filter a matched PCC list by country and/or genre (only items with a film are kept)."""
    if country:
        matched = [x for x in matched if x['film'] and x['film'].primary_country == country]
    if genre:
        matched = [x for x in matched if x['film'] and any(
            isinstance(g, dict) and g.get('name') == genre
            for g in (x['film'].genres or [])
        )]
    return matched


def _build_pcc_filter_lists(matched, country='', genre=''):
    """Return (genres, countries) filter lists, each aware of the other active filter."""
    for_genres = _filter_pcc_matched(matched, country=country) if country else matched
    for_countries = _filter_pcc_matched(matched, genre=genre) if genre else matched

    genres = sorted({
        g['name']
        for item in for_genres if item['film']
        for g in (item['film'].genres or [])
        if isinstance(g, dict) and g.get('name')
    })
    country_map = {}
    for item in for_countries:
        film = item['film']
        if not film or not film.primary_country:
            continue
        code = film.primary_country
        if code not in country_map:
            country_map[code] = COUNTRY_ISO.get(code, code)
    countries = sorted(country_map.items(), key=lambda x: x[1])
    return genres, countries


def pcc_schedule_json(request):
    sort = request.GET.get('sort', 'title_asc')
    country = request.GET.get('country', '')
    genre = request.GET.get('genre', '')
    offset = int(request.GET.get('offset', 0))

    matched = _get_sorted_pcc_screenings(sort)
    matched = _filter_pcc_matched(matched, country=country, genre=genre)
    total = len(matched)
    batch = matched[offset:offset + PCC_PAGE_SIZE]

    items = [
        {
            'id': item['film'].id if item['film'] else None,
            'title': item['film'].title if item['film'] else item['screening'].title,
            'poster_path': item['film'].poster_path if item['film'] else None,
            'pcc_url': item['screening'].pcc_url,
        }
        for item in batch
    ]

    return JsonResponse({
        'films': items,
        'has_more': (offset + PCC_PAGE_SIZE) < total,
        'next_offset': offset + PCC_PAGE_SIZE,
    })


class PCCSchedule(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"
    template_name = "kinorg/pcc_schedule.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort = self.request.GET.get('sort', 'title_asc')
        country = self.request.GET.get('country', '')
        genre = self.request.GET.get('genre', '')

        all_matched = _get_sorted_pcc_screenings(sort)
        genres, countries = _build_pcc_filter_lists(all_matched, country=country, genre=genre)
        matched = _filter_pcc_matched(all_matched, country=country, genre=genre)
        total = len(matched)

        context['screenings'] = matched[:PCC_PAGE_SIZE]
        context['has_more'] = total > PCC_PAGE_SIZE
        context['next_offset'] = PCC_PAGE_SIZE
        context['genres'] = genres
        context['countries'] = countries
        context['current_sort'] = sort
        context['current_country'] = country
        context['current_genre'] = genre
        context['collections'] = COLLECTIONS
        return context


class FilmDetail(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/film_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        movie_id = self.kwargs["id"]

        my_lists = FilmList.objects.filter(owner=user).order_by('-id')
        guest_lists = FilmList.objects.filter(guests=user).order_by('-id')

        film_reviews = WatchedFilm.objects.filter(film__id=movie_id, review_visible=True).exclude(mini_review__isnull=True).exclude(mini_review__exact='')
        context['user_flagged_ids'] = set(
            WatchedFilm.objects.filter(flagged_by=user).values_list('id', flat=True)
        )

        film_cache_key = f'tmdb_film_{movie_id}'
        film_data = cache.get(film_cache_key)
        if not film_data:
            film_data = get_tmdb_data(f"https://api.themoviedb.org/3/movie/{movie_id}?append_to_response=credits,keywords,videos&language=en-US")
            cache.set(film_cache_key, film_data, timeout=3600)

        providers_cache_key = f'tmdb_providers_{movie_id}'
        providers_data = cache.get(providers_cache_key)
        if not providers_data:
            providers_data = get_tmdb_data(f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers")
            cache.set(providers_cache_key, providers_data, timeout=3600)
        gb_providers = providers_data.get('results', {}).get('GB', {})
        context['watch_providers'] = gb_providers
        context['justwatch_url'] = gb_providers.get('link') or f"https://www.justwatch.com/uk/search?q={quote(film_data.get('title', ''))}"

        # Amazon affiliate link — shown when any Amazon provider is available
        amazon_tag = os.environ.get('AMAZON_ASSOCIATE_TAG', '')
        all_providers = (
            gb_providers.get('flatrate', []) +
            gb_providers.get('rent', []) +
            gb_providers.get('buy', [])
        )
        amazon_provider = next(
            (p for p in all_providers if 'amazon' in p.get('provider_name', '').lower()),
            None
        )
        if amazon_tag and amazon_provider:
            encoded_title = quote(film_data.get('title', ''))
            context['amazon_url'] = f"https://www.amazon.co.uk/s?k={encoded_title}&i=instant-video&tag={amazon_tag}"
            context['amazon_logo_path'] = amazon_provider.get('logo_path', '')
        else:
            context['amazon_url'] = None
            context['amazon_logo_path'] = None

        film_title = film_data.get('title', '')
        release_year = film_data.get('release_date', '')[:4]
        # Check manual FK link first, then fall back to title match
        pcc = PCCScreening.objects.filter(film_id=movie_id, hidden=False).first()
        if not pcc:
            pcc_matches = PCCScreening.objects.filter(title__iexact=film_title, hidden=False)
            if pcc_matches.count() > 1 and release_year:
                pcc = pcc_matches.filter(year=release_year).first()
            else:
                pcc = pcc_matches.first()
        context['pcc_url'] = pcc.pcc_url if pcc else None

        # Sort videos: trailers first, then everything else
        videos = film_data.get('videos', {}).get('results', [])
        videos.sort(key=lambda v: 'trailer' not in v.get('name', '').lower())
        if film_data.get('videos'):
            film_data['videos']['results'] = videos

        directors = [c for c in film_data.get('credits', {}).get('crew', []) if c['job'] == 'Director']
        context["directors"] = directors

        # Convert complex fields to JSON strings for the add_film form
        film_data['cast_json'] = json.dumps(film_data.get('credits', {}).get('cast', []))
        film_data['crew_json'] = json.dumps(film_data.get('credits', {}).get('crew', []))
        film_data['genres_json'] = json.dumps(film_data.get('genres', []))
        film_data['keywords_json'] = json.dumps(film_data.get('keywords', {}).get('keywords', []))
        film_data['production_companies_json'] = json.dumps(film_data.get('production_companies', []))
        countries = film_data.get('production_countries', [])
        country_codes = [c['iso_3166_1'] for c in countries if 'iso_3166_1' in c]
        film_data['production_countries_json'] = json.dumps(country_codes)

        for lst in my_lists:
            lst.contains_film = lst.films.filter(id=movie_id).exists()
        
        for lst in guest_lists:
            lst.contains_film = lst.films.filter(id=movie_id).exists()

        # Check if user has already reviewed this film
        try:
            watched = WatchedFilm.objects.get(user=user, film__id=movie_id)
        except WatchedFilm.DoesNotExist:
            watched = None
                
        film_obj = Film.objects.filter(pk=movie_id).first()
        context["similar_films"] = get_similar_films(movie_id, film_obj)

        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists
        context["film"] = film_data
        context["watched"] = watched
        context["film_reviews"] = film_reviews
        context["is_liked"] = LikedFilm.objects.filter(user=user, tmdb_id=movie_id).exists()

        return context


def add_film(request):

    if request.method == "POST":

        film_id = request.POST.get("id")

        def int_or_none(val):
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        try:
            film_data = {
                'title':                request.POST.get('title'),
                'release_date':         request.POST.get('release_date'),
                'poster_path':          request.POST.get('poster_path'),
                'backdrop_path':        request.POST.get('backdrop_path'),
                'overview':             request.POST.get('overview', ''),
                'runtime':              int_or_none(request.POST.get('runtime')),
                'cast':                 request.POST.get('cast'),
                'crew':                 request.POST.get('crew'),
                'genres':               request.POST.get('genres'),
                'keywords':             request.POST.get('keywords'),
                'production_companies': request.POST.get('production_companies'),
                'production_countries': request.POST.get('production_countries'),
                'primary_country': json.loads(request.POST.get('production_countries') or '[]')[0] if request.POST.get('production_countries') else '',
            }

            film_object, created = Film.objects.update_or_create(
                id=film_id,
                defaults=film_data
            )

            filmlist_object = FilmList.objects.get(pk=request.POST.get('list_id'))

            Addition.objects.get_or_create(
                film=film_object,
                film_list=filmlist_object,
                defaults={'added_by': request.user}
            )

        except Exception:
            return render(request, "kinorg/_toggle_error.html", {"message": "Couldn't add film"})

        return render(request, "kinorg/_toggle_button.html", {
            "film": film_object,
            "lst": filmlist_object,
            "is_in_list": True
        })

    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)


def remove_film(request):

    if request.method == "POST":

        try:
            my_list = FilmList.objects.get(pk=request.POST.get("list_id"))
            my_film = Film.objects.get(id=request.POST.get("id"))
            my_list.films.remove(my_film)

        except Exception:
            return render(request, "kinorg/_toggle_error.html", {"message": "Couldn't remove film"})

        return render(request, "kinorg/_toggle_button.html", {
            "film": my_film, 
            "lst": my_list,
            "is_in_list": False
            })

    else:

        return JsonResponse({'error': 'Invalid request'}, status=400)


def add_review(request):
    if request.method == "POST":

        user = request.user

        stars = request.POST.get("stars")  # Can be None
        mini_review = profanity.censor(request.POST.get("mini_review", "").strip())

        fields = [
            'title', 'release_date', 'poster_path', 'backdrop_path',
            'overview', 'runtime', 'cast', 'crew', 'genres', 'keywords',
            'production_companies'
        ]

        film_data = {field: request.POST.get(field) for field in fields}

        film_id = request.POST.get("id")

        film_object, created = Film.objects.update_or_create(
            id=film_id,
            defaults=film_data
        )

        # Prepare review data
        defaults = {}
        if stars:
            defaults['stars'] = int(stars)
        if mini_review:
            defaults['mini_review'] = mini_review

        # Create or update review
        watched, created = WatchedFilm.objects.update_or_create(
            user=user,
            film=film_object,
            defaults=defaults
        )

        # Redirect back to the film detail page
        return redirect('kinorg:film_detail', id=film_id)

    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)


def remove_review(request):
    
        if request.method == "POST":
    
            user = request.user
            film_id = request.POST.get("id")

            # Remove WatchedFilm record
            WatchedFilm.objects.filter(user=user, film__id=film_id).delete()
            
            # Redirect back to the film detail page
            return redirect('kinorg:film_detail', id=film_id)
    
        else:
    
            return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required(login_url='user_admin:login')
def flag_review(request, review_id):
    if request.method == 'POST':
        review = WatchedFilm.objects.filter(id=review_id).first()
        if not review:
            return JsonResponse({'error': 'Not found'}, status=404)
        if review.user == request.user:
            return JsonResponse({'error': 'Cannot flag your own review'}, status=400)
        if request.user in review.flagged_by.all():
            review.flagged_by.remove(request.user)
            flagged = False
        else:
            review.flagged_by.add(request.user)
            flagged = True
        return JsonResponse({'flagged': flagged})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required(login_url='user_admin:login')
def toggle_like(request, tmdb_id):
    if request.method == 'POST':
        liked, created = LikedFilm.objects.get_or_create(
            user=request.user,
            tmdb_id=tmdb_id,
            defaults={
                'title': request.POST.get('title', ''),
                'poster_path': request.POST.get('poster_path', ''),
            }
        )
        if not created:
            liked.delete()
            return JsonResponse({'liked': False})
        return JsonResponse({'liked': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)


class LikedFilms(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"
    template_name = "kinorg/liked_films.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['liked_films'] = LikedFilm.objects.filter(user=self.request.user).order_by('-liked_at')
        return context


class PersonCredits(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/person_credits.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        person_id = self.kwargs["person_id"]
        person_cache_key = f'tmdb_person_{person_id}'
        search_data = cache.get(person_cache_key)
        if not search_data:
            search_data = get_tmdb_data(f"https://api.themoviedb.org/3/person/{person_id}?append_to_response=movie_credits&language=en-US")
            cache.set(person_cache_key, search_data, timeout=3600)

        known_for = search_data.get('known_for_department', 'Acting')

        CREW_CATEGORIES = [
            ('Directing',     {'Director', 'Co-Director'}),
            ('Writing',       {'Writer', 'Screenplay', 'Original Screenplay', 'Story', 'Novel', 'Adaptation', 'Script'}),
            ('Producing',     {'Producer', 'Executive Producer', 'Co-Producer'}),
            ('Cinematography',{'Director of Photography', 'Cinematography'}),
            ('Editing',       {'Editor', 'Film Editing'}),
            ('Music',         {'Original Music Composer', 'Music', 'Composer'}),
            ('Production Design', {'Production Design', 'Production Designer'}),
            ('Costume Design',{'Costume Design', 'Costume Designer'}),
        ]

        cast_films = sorted(
            search_data['movie_credits'].get('cast', []),
            key=lambda f: f.get('popularity', 0), reverse=True
        )

        crew_tabs = {}
        seen = {}
        for member in search_data['movie_credits'].get('crew', []):
            job = member.get('job', '')
            for category, jobs in CREW_CATEGORIES:
                if job in jobs:
                    seen.setdefault(category, set())
                    if member['id'] not in seen[category]:
                        seen[category].add(member['id'])
                        crew_tabs.setdefault(category, [])
                        crew_tabs[category].append(member)
                    break
        for cat in crew_tabs:
            crew_tabs[cat].sort(key=lambda f: f.get('popularity', 0), reverse=True)

        DEPT_TO_TAB = {
            'Acting':             'acting',
            'Directing':          'directing',
            'Writing':            'writing',
            'Production':         'producing',
            'Camera':             'cinematography',
            'Editing':            'editing',
            'Sound':              'music',
            'Art':                'productiondesign',
            'Costume & Make-Up':  'costumedesign',
        }
        all_tab_keys = (['acting'] if cast_films else []) + [k.lower().replace(' ', '') for k in crew_tabs.keys()]
        preferred = DEPT_TO_TAB.get(known_for, 'acting')
        default_tab = preferred if preferred in all_tab_keys else (all_tab_keys[0] if all_tab_keys else 'acting')

        context["name"] = search_data["name"]
        context["profile_path"] = search_data.get("profile_path")
        context["biography"] = search_data.get("biography", "")
        context["cast_films"] = cast_films
        context["crew_tabs"] = crew_tabs
        context["default_tab"] = default_tab

        return context


class Invitations(LoginRequiredMixin, ListView):

    login_url = "user_admin:login"

    template_name = "kinorg/invitations.html"

    model = Invitation

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user

        queryset = queryset.filter(to_user=user).exclude(accepted=True)

        return queryset


def invite_guest(request):

    if request.method == "POST":

        users = get_user_model()

        from_user = request.user

        to_username = request.POST.get("username") 

        list_object = FilmList.objects.get(pk=request.POST.get("list_id"))

        try:
            to_user = users.objects.get(username=to_username)
        except users.DoesNotExist:
            return JsonResponse({'success': False, 'message': f"The user '{to_username}' does not exist."})

        try:
            send_invitation(list_object, to_user, from_user)
            invitation = Invitation.objects.get(film_list=list_object, to_user=to_user)
            return JsonResponse({'success': True, 'message': 'Invitation sent!', 'username': to_username, 'invitation_id': invitation.id})
        except PermissionError as error:
            return JsonResponse({'success': False, 'message': str(error)})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"An unexpected error occurred: {str(e)}"})

    else:

        return redirect("kinorg:my_lists")


def cancel_invite(request):

    if request.method == "POST":
        try:
            invitation = Invitation.objects.get(
                pk=request.POST.get("invitation_id"),
                film_list__owner=request.user,
            )
            invitation.delete()
            return JsonResponse({'success': True})
        except Invitation.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invitation not found.'})

    return JsonResponse({'success': False, 'message': 'Invalid request.'})


def remove_guest(request):

    if request.method == "POST":
        try:
            film_list = FilmList.objects.get(pk=request.POST.get("list_id"), owner=request.user)
            user = get_user_model().objects.get(pk=request.POST.get("user_id"))
            film_list.guests.remove(user)
            Invitation.objects.filter(film_list=film_list, to_user=user).delete()
            return JsonResponse({'success': True})
        except (FilmList.DoesNotExist, get_user_model().DoesNotExist):
            return JsonResponse({'success': False, 'message': 'Not found.'})

    return JsonResponse({'success': False, 'message': 'Invalid request.'})


def invite_result(request):

    return render(request, "kinorg/invite_result.html")


def accept_invite(request):

    if request.method == "POST":

        list_id = request.POST.get("list_id")
        user_id = request.POST.get("user_id")

        users = get_user_model()

        user = users.objects.get(
            pk=user_id
            )

        list_object = FilmList.objects.get(
            pk=list_id
            )

        accept_invitation(list_object, user)

        return redirect("kinorg:my_lists")

    else:

        return redirect("kinorg:my_lists")


def decline_invite(request):

    if request.method == "POST":

        list_id = request.POST.get("list_id")
        user_id = request.POST.get("user_id")

        users = get_user_model()

        user = users.objects.get(pk=user_id)

        list_object = FilmList.objects.get(pk=list_id)

        decline_invitation(list_object, user)

        return redirect("kinorg:my_lists")

    else:

        return redirect("kinorg:my_lists")
    
 
def film_lists_for_film(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    film_id = request.GET.get('film_id')
    if not film_id:
        return JsonResponse({'error': 'Missing film_id'}, status=400)

    my_lists = FilmList.objects.filter(owner=request.user).order_by('-id')
    guest_lists = FilmList.objects.filter(guests=request.user).order_by('-id')

    def serialize(lst):
        return {
            'id': lst.id,
            'title': lst.title,
            'sqid': lst.sqid,
            'contains_film': lst.films.filter(id=film_id).exists(),
        }

    return JsonResponse({
        'my_lists': [serialize(lst) for lst in my_lists],
        'guest_lists': [serialize(lst) for lst in guest_lists],
    })


def add_film_by_tmdb_id(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    film_id = request.POST.get('film_id')
    list_id = request.POST.get('list_id')

    try:
        filmlist_object = FilmList.objects.get(pk=list_id)
        if filmlist_object.owner != request.user and request.user not in filmlist_object.guests.all():
            return JsonResponse({'error': 'Permission denied'}, status=403)

        film_data = get_tmdb_data(
            f"https://api.themoviedb.org/3/movie/{film_id}?append_to_response=credits,keywords&language=en-US"
        )

        film_object, _ = Film.objects.update_or_create(
            id=film_id,
            defaults={
                'title': film_data.get('title', ''),
                'release_date': film_data.get('release_date') or '1900-01-01',
                'poster_path': film_data.get('poster_path') or '',
                'backdrop_path': film_data.get('backdrop_path') or '',
                'overview': film_data.get('overview', ''),
                'runtime': film_data.get('runtime'),
                'genres': film_data.get('genres', []),
                'cast': film_data.get('credits', {}).get('cast', []),
                'crew': film_data.get('credits', {}).get('crew', []),
                'keywords': film_data.get('keywords', {}).get('keywords', []),
                'production_companies': film_data.get('production_companies', []),
                'production_countries': [c['iso_3166_1'] for c in film_data.get('production_countries', []) if 'iso_3166_1' in c],
                'primary_country': (film_data.get('production_countries') or [{}])[0].get('iso_3166_1', ''),
            }
        )

        Addition.objects.get_or_create(
            film=film_object,
            film_list=filmlist_object,
            defaults={'added_by': request.user}
        )

        return JsonResponse({'success': True})

    except FilmList.DoesNotExist:
        return JsonResponse({'error': 'List not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def remove_film_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        film_list = FilmList.objects.get(pk=request.POST.get('list_id'))
        if film_list.owner != request.user and request.user not in film_list.guests.all():
            return JsonResponse({'error': 'Permission denied'}, status=403)
        film = Film.objects.get(id=request.POST.get('film_id'))
        film_list.films.remove(film)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def no_access(request):
    return render(request, "kinorg/no_access.html")
