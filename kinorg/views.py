import os

import requests

from django.shortcuts import render, redirect

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.urls import reverse_lazy

from .models import Film, FilmList, Addition


def home(request):

    if request.user.is_authenticated:

        return redirect("kinorg:my_lists")

    else:

        api_key = os.environ.get('TMDB_KEY')

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        config_url = "https://api.themoviedb.org/3/configuration"
        config_response = requests.get(config_url, headers=headers)
        config_data = config_response.json()

        films = Film.objects.all()

        context = {"films": films, "config_data": config_data["images"]}

        return render(request, "kinorg/home.html", context)


def search(request):

    api_key = os.environ.get('TMDB_KEY')

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
        
    query = request.GET.get('query')

    config_url = "https://api.themoviedb.org/3/configuration"
    search_url = f"https://api.themoviedb.org/3/search/movie?query={query}&include_adult=false&language=en-US&page=1"

    config_response = requests.get(config_url, headers=headers)
    search_response = requests.get(search_url, headers=headers)

    config_data = config_response.json()
    search_data = search_response.json()

    context = {"film_list": search_data["results"], "config_data": config_data["images"]}

    return render(request, "kinorg/search.html", context)


class CreateList(LoginRequiredMixin, CreateView):

    login_url = "user_admin:login"

    model = FilmList
    fields = ["title"]
    template_name_suffix = "_create_form"
    success_url = reverse_lazy("kinorg:my_lists")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MyLists(LoginRequiredMixin, ListView):
    
    login_url = "user_admin:login"

    model = FilmList
    template = "kinorg/my_lists.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        my_lists = FilmList.objects.filter(owner=user)
        guest_lists = FilmList.objects.filter(guests=user)

        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists

        return context


class ListDetail(LoginRequiredMixin, UserPassesTestMixin, DetailView):

    login_url = "user_admin:login"

    model = FilmList

    def test_func(self):
        list_object = self.get_object()

        return list_object.owner == self.request.user or self.request.user in list_object.guests.all()

    def handle_no_permission(self):
        return redirect("kinorg:no_access")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        api_key = os.environ.get('TMDB_KEY')

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        config_url = "https://api.themoviedb.org/3/configuration"
        config_response = requests.get(config_url, headers=headers)
        config_data = config_response.json()

        context["config_data"] = config_data["images"]

        return context


class FilmDetail(LoginRequiredMixin, TemplateView):

    login_url = "user_admin:login"

    template_name = "kinorg/film_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        my_lists = FilmList.objects.filter(owner=user)
        guest_lists = FilmList.objects.filter(guests=user)

        context["my_lists"] = my_lists
        context["guest_lists"] = guest_lists

        movie_id = self.kwargs["movie_id"]

        api_key = os.environ.get("TMDB_KEY")

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        config_url = "https://api.themoviedb.org/3/configuration"
        get_url = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"

        config_response = requests.get(config_url, headers=headers)
        get_response = requests.get(get_url, headers=headers)

        config_data = config_response.json()
        film_data = get_response.json()

        context["film"] = film_data
        context["config_data"] = config_data["images"]

        return context



def add_film(request):

    if request.method == "POST":

        title = request.POST.get("title")
        year = request.POST.get("year")
        movie_id = request.POST.get("movie_id")
        poster_path = request.POST.get("poster_path")

        user = request.user
        list_id = request.POST.get("list_id")

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

 
def no_access(request):
    return render(request, "kinorg/no_access.html")







