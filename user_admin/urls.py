from django.urls import path

from . import views

app_name = "user_admin"
urlpatterns = [
    path("login/", views.SiteLoginView.as_view(), name="login"),
    path("logout/", views.SiteLogoutView.as_view(), name="logout"),
    path("adduser/", views.AddUserView.as_view(), name="adduser"),
    path("success/", views.success_page, name="success_page")
    ]