import os

import re
import requests
import json

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse

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

    ordered_results = sorted(search_results, key=lambda i: i['popularity'], reverse=True)

    return ordered_results


def films_and_people(search_data):

    filtered_films = [film for film in search_data["results"] if film['media_type'] == 'movie' or film['media_type'] == 'person']

    return filtered_films


def send_invitation(invited_list, to_user, from_user):

    users = get_user_model()

    if from_user != invited_list.owner:
        raise PermissionError("You don't have permission!")

    elif to_user == invited_list.owner:
        raise PermissionError("You're already the owner!")

    elif users.objects.filter(email=to_user).exists():
        raise PermissionError("User does not exist!")

    elif Invitation.objects.filter(to_user=to_user, film_list=invited_list):
        raise PermissionError("Already invited!")

    elif from_user == invited_list.owner:
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


# Functions END ------------------------------------------------------------>


class Home(ListView):

    model = Film
    template_name = "kinorg/home.html"


class Search(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/search.html"

    def get(self, request, *args, **kwargs):
        # If no query is provided, redirect to home
        if not request.GET.get('query'):
            return redirect('kinorg:home')

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Search based on query content -------------------------------------
        query = self.request.GET.get('query').strip()

        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)

        # if there's a year in the query
        if year_match:
            year = year_match.group(1)
            title = query.replace(year, '').strip()

            # if there's also text
            if title:
                search_url = f"https://api.themoviedb.org/3/search/movie?query={title}&include_adult=false&language=en-US&primary_release_year={year}&page=1"
                search_data = get_tmdb_data(search_url)
                ordered_results = order_by_popularity(search_data["results"])

            # if there's just a year
            else:
                search_url = f"https://api.themoviedb.org/3/search/multi?query={year}&include_adult=false&language=en-US&page=1"
                search_data = get_tmdb_data(search_url)
                filtered_films = films_and_people(search_data)
                ordered_results = order_by_popularity(filtered_films)

        #if it's just text
        else:
            search_url = f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US&page=1"
            search_data = get_tmdb_data(search_url)
            filtered_films = films_and_people(search_data)
            ordered_results = order_by_popularity(filtered_films)
        # -------------------------------------------------------------------

        context["query"] = query
        context["results_list"] = ordered_results

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

        # Check for success or error messages in session
        if 'invitation_sent' in self.request.session:
            messages.success(self.request, "Invitation sent successfully!")
            self.request.session.pop('invitation_sent') 

        if 'invitation_error' in self.request.session:
            messages.error(self.request, self.request.session['invitation_error']) 
            self.request.session.pop('invitation_error')

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

        film_data = get_tmdb_data(f"https://api.themoviedb.org/3/movie/{movie_id}?append_to_response=credits,keywords,videos&language=en-US")

        directors = [c for c in film_data.get('credits', {}).get('crew', []) if c['job'] == 'Director']
        context["directors"] = directors

        # Convert complex fields to JSON strings for the add_film form
        film_data['cast_json'] = json.dumps(film_data['credits']['cast'])
        film_data['crew_json'] = json.dumps(film_data['credits']['crew'])
        film_data['genres_json'] = json.dumps(film_data['genres'])
        film_data['keywords_json'] = json.dumps(film_data['keywords']['keywords'])
        film_data['production_companies_json'] = json.dumps(film_data['production_companies'])

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

        return context


def add_film(request):

    if request.method == "POST":

        user = request.user

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

        filmlist_object = FilmList.objects.get(pk=request.POST.get('list_id'))

        addition_object = Addition.objects.create(
            film=film_object,
            film_list=filmlist_object,
            added_by=user
        )

        return render(request, "kinorg/_toggle_button.html", {
            "film": film_object, 
            "lst": filmlist_object,
            "is_in_list": True
        })

    else:

        return JsonResponse({'error': 'Invalid request'}, status=400)


def remove_film(request):

    if request.method == "POST":

        my_list = FilmList.objects.get(pk=request.POST.get("list_id"))
        my_film = Film.objects.get(id=request.POST.get("id"))
        my_list.films.remove(my_film)

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

        films = search_data['movie_credits'].get('cast', []) + [f for f in search_data['movie_credits'].get('crew', []) if f.get('job') == 'Director'
]

        cast_films = sorted(search_data['movie_credits'].get('cast', []), key=lambda i: i['popularity'], reverse=True)
        directed_films = sorted(
            [f for f in search_data['movie_credits'].get('crew', []) if f.get('job') == 'Director'],
            key=lambda i: i['popularity'], reverse=True
        )

        # Determine active tab - only relevant if both lists have films
        active_tab = self.request.GET.get('tab', 'directed') if directed_films and cast_films else None

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

        to_user_email = request.POST.get("user_email")

        list_object = FilmList.objects.get(pk=request.POST.get("list_id"))

        try:
            to_user = users.objects.get(email=to_user_email)
        except users.DoesNotExist:
            request.session['invitation_error'] = "The user with email '{}' does not exist.".format(to_user_email)
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
