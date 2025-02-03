from django.urls import path

from . import views

app_name = "kinorg"
urlpatterns = [
    path("", views.Home.as_view(), name="home"),
    path("search/", views.Search.as_view(), name="search"),
    path("search-user/", views.SearchUser.as_view(), name="search_user"),
    path("lists/", views.MyLists.as_view(), name="my_lists"),
    path("lists/<slug>/", views.ListDetail.as_view(), name="list"),
    path("create/", views.CreateList.as_view(), name="create_list"),
    path("add-film/", views.add_film, name="add_film"),
    path("remove-film/", views.remove_film, name="remove_film"),
    path("film-detail/<int:movie_id>", views.FilmDetail.as_view(), name="film_detail"),
    path("person-credits/<int:person_id>", views.PersonCredits.as_view(), name="person_credits"),
    path("invitations/", views.Invitations.as_view(), name="invitations"),
    path("invite-guest/", views.invite_guest, name="invite_guest"),
    path("invite-result/", views.invite_result, name="invite_result"),
    path("accept-invite/", views.accept_invite, name="accept_invite"),
    path("decline-invite/", views.decline_invite, name="decline_invite"),
    path("no-access/", views.no_access, name="no_access")
    ]