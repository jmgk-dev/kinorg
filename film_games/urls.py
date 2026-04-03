from django.urls import path

from . import views

app_name = 'film_games'

urlpatterns = [
    path('game/', views.hub, name='hub'),
    path('game/higher-lower/', views.higher_lower, name='higher_lower'),
    path('game/higher-lower/pair/', views.higher_lower_pair, name='higher_lower_pair'),
    path('game/higher-lower/answer/', views.higher_lower_answer, name='higher_lower_answer'),
]
