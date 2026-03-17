import os
import re
import requests
import json
from urllib.parse import quote

from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse, JsonResponse

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.urls import reverse_lazy

from .models import Film, FilmList, Addition, Invitation, WatchedFilm


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
        raw = data.get('results', [])
        raw = [r for r in raw if r.get('media_type') in ('movie', 'person')]

    # Apply filter
    if filter_type == 'films':
        raw = [r for r in raw if r.get('media_type') == 'movie']
    elif filter_type == 'people':
        raw = [r for r in raw if r.get('media_type') == 'person']

    # Exact title matches first, then by popularity (avoids burying older/less popular films)
    query_lower = clean_query.lower()
    def sort_key(r):
        title = (r.get('title') or r.get('name') or '').lower()
        return (title != query_lower, -r.get('popularity', 0))
    raw = sorted(raw, key=sort_key)

    results = []
    for r in raw[:10]:
        if r.get('media_type') == 'movie':
            results.append({
                'id': r['id'],
                'title': r.get('title', ''),
                'year': r.get('release_date', '')[:4],
                'poster_path': r.get('poster_path') or '',
                'media_type': 'movie',
                'profile_path': '',
            })
        elif r.get('media_type') == 'person':
            results.append({
                'id': r['id'],
                'title': r.get('name', ''),
                'year': '',
                'poster_path': '',
                'media_type': 'person',
                'profile_path': r.get('profile_path') or '',
            })

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

        my_lists = FilmList.objects.filter(owner=user).order_by('-id')
        guest_lists = FilmList.objects.filter(guests=user).order_by('-id')
        invitations = Invitation.objects.filter(to_user=user).exclude(accepted=True)

        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists
        context["invitations"] = invitations

        return context


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

        context['invitations'] = invitations

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

        film_reviews = WatchedFilm.objects.filter(film__id=movie_id).exclude(mini_review__isnull=True).exclude(mini_review__exact='')

        film_data = get_tmdb_data(f"https://api.themoviedb.org/3/movie/{movie_id}?append_to_response=credits,keywords,similar,videos&language=en-US")

        providers_data = get_tmdb_data(f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers")
        gb_providers = providers_data.get('results', {}).get('GB', {})
        context['watch_providers'] = gb_providers
        context['justwatch_url'] = f"https://www.justwatch.com/uk/search?q={quote(film_data.get('title', ''))}"

        # Amazon affiliate link — shown when any Amazon provider is available
        amazon_tag = os.environ.get('AMAZON_ASSOCIATE_TAG', '')
        all_providers = (
            gb_providers.get('flatrate', []) +
            gb_providers.get('rent', []) +
            gb_providers.get('buy', [])
        )
        amazon_provider_ids = {
            p['provider_id'] for p in all_providers
            if 'amazon' in p.get('provider_name', '').lower()
        }
        if amazon_tag and amazon_provider_ids:
            encoded_title = quote(film_data.get('title', ''))
            context['amazon_url'] = f"https://www.amazon.co.uk/s?k={encoded_title}&i=instant-video&tag={amazon_tag}"
        else:
            context['amazon_url'] = None
        context['amazon_provider_ids'] = amazon_provider_ids

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

        for lst in my_lists:
            lst.contains_film = lst.films.filter(id=movie_id).exists()
        
        for lst in guest_lists:
            lst.contains_film = lst.films.filter(id=movie_id).exists()

        # Check if user has already reviewed this film
        try:
            watched = WatchedFilm.objects.get(user=user, film__id=movie_id)
        except WatchedFilm.DoesNotExist:
            watched = None
                
        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists
        context["film"] = film_data
        context["watched"] = watched
        context["film_reviews"] = film_reviews

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
        mini_review = request.POST.get("mini_review", "").strip()

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


class PersonCredits(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/person_credits.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        person_id = self.kwargs["person_id"]
        search_data = get_tmdb_data(f"https://api.themoviedb.org/3/person/{person_id}?append_to_response=movie_credits&language=en-US")

        known_for = search_data.get('known_for_department', 'Acting')

        films = search_data['movie_credits'].get('cast', []) + [f for f in search_data['movie_credits'].get('crew', []) if f.get('job') == 'Director'
]

        cast_films = sorted(search_data['movie_credits'].get('cast', []), key=lambda film: film['popularity'], reverse=True)
        directed_films = sorted(
            [f for f in search_data['movie_credits'].get('crew', []) if f.get('job') == 'Director'],
            key=lambda film: film['popularity'], reverse=True
        )

        # Determine active tab - only relevant if both lists have film
        default_tab = 'directing' if known_for == 'Directing' else 'acting'
        active_tab = self.request.GET.get('tab', default_tab)

        context["name"] = search_data["name"]
        context["cast_films"] = cast_films
        context["directed_films"] = directed_films
        context["active_tab"] = active_tab

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
