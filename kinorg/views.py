import os

import re
import requests

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.urls import reverse_lazy

from .models import Film, FilmList, Addition, Invitation

# Functions ------------------------------------------------------------>

def get_search(url):

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.environ.get('TMDB_KEY')}"
    }

    search_response = requests.get(url, headers=headers)
    search_data = search_response.json()

    return search_data


def build_add_remove_lists(film_id, film_lists):

    to_add = []
    to_remove = []

    for lst in film_lists:
        if film_id in lst.films.values_list('movie_id', flat=True):
            to_remove.append((lst.title, lst.pk, lst.owner, lst.sqid))
        else:
            to_add.append((lst.title, lst.pk, lst.owner, lst.sqid))

    return to_add, to_remove


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

        # Search
        query = self.request.GET.get('query').strip()

        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)

        if year_match:
            year = year_match.group(1)
            title = query.replace(year, '').strip()

            if title:
                search_url = f"https://api.themoviedb.org/3/search/movie?query={title}&include_adult=false&language=en-US&primary_release_year={year}&page=1"
                search_data = get_search(search_url)
                search_results = search_data["results"]
                search_results = sorted(search_results, key=lambda i: i['popularity'], reverse=True)

            else:
                search_url = f"https://api.themoviedb.org/3/search/multi?query={year}&include_adult=false&language=en-US&page=1"
                search_data = get_search(search_url)
                search_results = search_data["results"]
                search_results = sorted(search_results, key=lambda i: i['popularity'], reverse=True)

        else:
            search_url = f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US&page=1"
            search_data = get_search(search_url)
            filtered_films = [film for film in search_data["results"] if film['media_type'] == 'movie' or film['media_type'] == 'person']
            search_results = sorted(filtered_films, key=lambda i: i['popularity'], reverse=True)

        # Build lists
        my_lists = FilmList.objects.filter(owner=user)
        guest_lists = FilmList.objects.filter(guests=user)

        for lst in my_lists:
            lst.movie_ids = lst.films.values_list('movie_id', flat=True)
        for glst in guest_lists:
            glst.movie_ids = glst.films.values_list('movie_id', flat=True)

        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists
        context["query"] = query
        context["results_list"] = search_results

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
        movie_id = self.kwargs["movie_id"]

        my_lists = FilmList.objects.filter(owner=user)
        guest_lists = FilmList.objects.filter(guests=user)

        get_url = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"

        film_data = get_search(get_url)

        to_add, to_remove = build_add_remove_lists(
            film_data['id'], 
            my_lists
            )

        to_add_g, to_remove_g = build_add_remove_lists(
            film_data['id'], 
            guest_lists
            )
        
        context["to_add"] = to_add
        context["to_remove"] = to_remove
        context["to_add_g"] = to_add_g
        context["to_remove_g"] = to_remove_g           
        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists
        context["film"] = film_data

        return context


class PersonCredits(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/person_credits.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        my_lists = FilmList.objects.filter(owner=user)
        guest_lists = FilmList.objects.filter(guests=user)

        for lst in my_lists:
            lst.movie_ids = lst.films.values_list('movie_id', flat=True)
        for lst in guest_lists:
            lst.movie_ids = lst.films.values_list('movie_id', flat=True)

        person_id = self.kwargs["person_id"]
        get_url = f"https://api.themoviedb.org/3/person/{person_id}?append_to_response=movie_credits&language=en-US"
        search_data = get_search(get_url)

        films = search_data['movie_credits']['cast']

        sorted_films = sorted(films, key=lambda i: i['popularity'], reverse=True)

        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists
        context["name"] = search_data["name"]
        context["results"] = sorted_films

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


def add_film(request):

    if request.method == "POST":

        title = request.POST.get("title")
        year = request.POST.get("year")
        movie_id = request.POST.get("movie_id")
        poster_path = request.POST.get("poster_path")
        list_id = request.POST.get("list_id")

        filmlist_object = FilmList.objects.get(pk=list_id)
        list_sqid = filmlist_object.sqid

        user = request.user

        film_object, created = Film.objects.get_or_create(
            title=title,
            year=year,
            movie_id=movie_id,
            poster_path=poster_path
            )

        addition_object = Addition.objects.create(
            film=film_object,
            film_list=FilmList.objects.get(pk=list_id),
            added_by=user
            )

        return render(request, "kinorg/success_add_message.html")

    else:

        return JsonResponse({'error': 'Invalid request'}, status=400)


def remove_film(request):

    if request.method == "POST":

        list_id = request.POST.get("list_id")
        movie_id = request.POST.get("movie_id")
        sqid = request.POST.get("sqid")

        my_list = FilmList.objects.get(pk=list_id)
        my_film = Film.objects.get(movie_id=movie_id)
        my_list.films.remove(my_film)

        return render(request, "kinorg/success_remove_message.html")

    else:

        return JsonResponse({'error': 'Invalid request'}, status=400)


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







