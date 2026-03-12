import os

import re
import requests
import json

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
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

    data = get_tmdb_data(
        f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US&page=1"
    )

    raw = data.get('results', [])

    # Keep only movies and people
    raw = [r for r in raw if r.get('media_type') in ('movie', 'person')]

    # Apply filter
    if filter_type == 'films':
        raw = [r for r in raw if r.get('media_type') == 'movie']
    elif filter_type == 'people':
        raw = [r for r in raw if r.get('media_type') == 'person']

    # Sort by popularity descending so Lynch/Cameron surface first
    raw = sorted(raw, key=lambda r: r.get('popularity', 0), reverse=True)

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


class SearchUser(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/user_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        users = get_user_model()

        query = self.request.GET.get('query')

        if query:
            user_results = users.objects.filter(username__icontains=username_query)
        user_results = users.objects.all()

        context["user_results"] = user_results

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

        my_lists = FilmList.objects.filter(owner=user)
        guest_lists = FilmList.objects.filter(guests=user)
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

        if 'invitation_sent' in self.request.session:
            messages.success(self.request, "Invitation sent successfully!")
            self.request.session.pop('invitation_sent')

        if 'invitation_error' in self.request.session:
            messages.error(self.request, self.request.session['invitation_error'])
            self.request.session.pop('invitation_error')

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

        my_lists = FilmList.objects.filter(owner=user)
        guest_lists = FilmList.objects.filter(guests=user)

        film_reviews = WatchedFilm.objects.filter(film__id=movie_id).exclude(mini_review__isnull=True).exclude(mini_review__exact='')

        film_data = get_tmdb_data(f"https://api.themoviedb.org/3/movie/{movie_id}?append_to_response=credits,keywords,similar,videos&language=en-US")

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
            request.session['invitation_error'] = "The user '{}' does not exist.".format(to_username)
            return redirect('kinorg:list', list_object.sqid)

        try:
            send_invitation(list_object, to_user, from_user)
            request.session['invitation_sent'] = True
            return redirect('kinorg:list', list_object.sqid)
        except PermissionError as error:
            request.session['invitation_error'] = str(error)
            return redirect('kinorg:list', list_object.sqid)
        except Exception as e:
            request.session['invitation_error'] = f"An unexpected error occurred: {str(e)}"
            return redirect('kinorg:list', list_object.sqid) 

    else:

        return redirect("kinorg:my_lists")


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
    
 
def no_access(request):
    return render(request, "kinorg/no_access.html")
