from django.urls import path

from django.contrib.auth import views as auth_views
from . import views

app_name = "user_admin"
urlpatterns = [
    path("login/", views.SiteLogin.as_view(), name="login"),
    path("logout/", views.SiteLogout.as_view(), name="logout"),
    # path("adduser/", views.AddUser.as_view(), name="adduser"),
    path("success/", views.success_page, name="success_page"),


    path(
        "reset-password/",
        views.ResetPassword.as_view(),
        name="reset_password"
        ),

    path(
        "reset-password-confirm/<uidb64>/<token>/", 
        views.ResetPasswordConfirm.as_view(), 
        name='reset_password_confirm'
        ),


    path(
        "reset-password/done",
        views.ResetPasswordDone.as_view(),
        name="reset_password_done"
        ),


    path("reset-password-complete",
        views.ResetPasswordComplete.as_view(),
        name="reset_password_complete"
        )
    ]