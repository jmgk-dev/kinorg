import os

import requests

from django.shortcuts import render, redirect
from django.conf import settings

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.urls import reverse_lazy

from .models import Film, FilmList, Addition, Invitation


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
            to_remove.append((lst.title, lst.pk, lst.owner))
        else:
            to_add.append((lst.title, lst.pk, lst.owner))

    return to_add, to_remove


class Home(ListView):

    model = Film
    template_name = "kinorg/home.html"


class Search(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        query = self.request.GET.get('query')

        # search_url = f"https://api.themoviedb.org/3/search/movie?query={query}&include_adult=false&language=en-US&page=1"
        search_url = f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US&page=1"


        search_data = get_search(search_url)

        context["film_list"] = search_data["results"]

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

    def test_func(self):
        list_object = self.get_object()

        return list_object.owner == self.request.user or self.request.user in list_object.guests.all()

    def handle_no_permission(self):
        return redirect("kinorg:no_access")


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

        person_id = self.kwargs["person_id"]

        get_url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?language=en-US"

        credits = get_search(get_url)

        context["credits"] = credits

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

        return redirect("kinorg:list", list_id)

    else:

        return redirect("kinorg:my_lists")


def remove_film(request):

    if request.method == "POST":

        list_id = request.POST.get("list_id")
        movie_id = request.POST.get("movie_id")

        my_list = FilmList.objects.get(pk=list_id)
        my_film = Film.objects.get(movie_id=movie_id)
        my_list.films.remove(my_film)

        return redirect("kinorg:list", list_id)

    else:

        return redirect("kinorg:my_lists")


def invite_guest(request):

    if request.method == "POST":

        users = get_user_model()

        to_user = users.objects.get(
            email=request.POST.get("user_email")
            )

        from_user = request.user

        list_object = FilmList.objects.get(
            pk=request.POST.get("list_id")
            )

        try:
            list_object.send_invitation(to_user, from_user)
        except PermissionError as error:
            message = str(error)
            return render(request, "kinorg/invite_result.html", {"message": message})

        return render(request, "kinorg/invite_result.html", {"message": "Invitation sent!"})

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

        list_object.accept_invitation(user)

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

        list_object.decline_invitation(user)

        return redirect("kinorg:my_lists")

    else:

        return redirect("kinorg:my_lists")
    
 
def no_access(request):
    return render(request, "kinorg/no_access.html")







