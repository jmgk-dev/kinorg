from django.contrib import admin
from django.core.cache import cache
from django.utils.html import format_html

from .models import GameFilm, DailyFramed, GameResult


@admin.register(GameFilm)
class GameFilmAdmin(admin.ModelAdmin):
    list_display = ['poster_thumbnail', 'title', 'release_date', 'vote_count', 'approved', 'used_framed_on']
    list_display_links = ['title']
    list_filter = ['approved']
    list_editable = ['approved']
    search_fields = ['title']
    ordering = ['-vote_count']

    def poster_thumbnail(self, obj):
        if not obj.poster_path:
            return '—'
        config = cache.get('tmdb_config') or {}
        base_url = config.get('secure_base_url', 'https://image.tmdb.org/t/p/')
        return format_html('<img src="{}w92{}" style="height:60px;border-radius:4px;">', base_url, obj.poster_path)
    poster_thumbnail.short_description = 'Poster'


@admin.register(DailyFramed)
class DailyFramedAdmin(admin.ModelAdmin):
    list_display = ['date', 'film']
    ordering = ['-date']


@admin.register(GameResult)
class GameResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'game', 'date', 'score']
    list_filter = ['game']
    ordering = ['-date']
