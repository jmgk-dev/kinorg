from django.urls import path
# from django.views.generic import TemplateView

from . import views

app_name = "kinorg"
urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("lists/", views.MyLists.as_view(), name="my_lists"),
    path("lists/<int:pk>", views.ListDetail.as_view(), name="list"),
    path("create/", views.CreateList.as_view(), name="create_list"),
    # path("add-film/", views.AddFilmToList.as_view(), name="add_film"),
    path("add-film/", views.add_film, name="add_film"),
    path("remove-film/", views.remove_film, name="remove_film"),
    path("film-detail/<int:movie_id>", views.FilmDetail.as_view(), name="film_detail"),
    path("no-access", views.no_access, name="no_access")
    ]