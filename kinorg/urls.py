from django.urls import path

from . import views

app_name = "kinorg"
urlpatterns = [
    path("", views.Home.as_view(), name="home"),
    path("search/", views.Search.as_view(), name="search"),
    path("lists/", views.MyLists.as_view(), name="my_lists"),
    path("lists/<slug>/", views.ListDetail.as_view(), name="list"),
    path("lists/<slug>/additions/", views.list_additions_json, name="list_additions_json"),
    path("create/", views.CreateList.as_view(), name="create_list"),
    path("add-film/", views.add_film, name="add_film"),
    path("remove-film/", views.remove_film, name="remove_film"),
    path('add-review/', views.add_review, name='add_review'),
    path("film-detail/<int:id>", views.FilmDetail.as_view(), name="film_detail"),
    path("person-credits/<int:person_id>", views.PersonCredits.as_view(), name="person_credits"),
    path("invitations/", views.Invitations.as_view(), name="invitations"),
    path("invite-guest/", views.invite_guest, name="invite_guest"),
    path("cancel-invite/", views.cancel_invite, name="cancel_invite"),
    path("remove-guest/", views.remove_guest, name="remove_guest"),
    path("invite-result/", views.invite_result, name="invite_result"),
    path("accept-invite/", views.accept_invite, name="accept_invite"),
    path("decline-invite/", views.decline_invite, name="decline_invite"),
    path("film-autocomplete/", views.film_autocomplete, name="film_autocomplete"),
    path("user-autocomplete/", views.user_autocomplete, name="user_autocomplete"),
    path("no-access/", views.no_access, name="no_access"),
    path("about/", views.About.as_view(), name="about"),
    path("film-lists/", views.film_lists_for_film, name="film_lists_for_film"),
    path("add-film-by-id/", views.add_film_by_tmdb_id, name="add_film_by_tmdb_id"),
    path("remove-film-ajax/", views.remove_film_ajax, name="remove_film_ajax"),
    path("remove-review/", views.remove_review, name="remove_review"),
    path("flag-review/<int:review_id>/", views.flag_review, name="flag_review"),
    path("like/<int:tmdb_id>/", views.toggle_like, name="toggle_like"),
    path("liked/", views.LikedFilms.as_view(), name="liked_films"),
    path("collections/<str:tag>/", views.CollectionDetail.as_view(), name="collection_detail"),
    path("collections/<str:tag>/films/", views.collection_films_json, name="collection_films_json"),
    path("pcc/", views.PCCSchedule.as_view(), name="pcc_schedule"),
    ]