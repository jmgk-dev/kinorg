from django.contrib import admin
from .models import WatchedFilm, Film, FilmList, PCCScreening


@admin.register(WatchedFilm)
class WatchedFilmAdmin(admin.ModelAdmin):
    list_display = ('user', 'film', 'stars', 'short_review', 'flag_count', 'review_visible')
    list_filter = ('review_visible', 'stars')
    list_editable = ('review_visible',)
    search_fields = ('user__username', 'film__title', 'mini_review')
    ordering = ('-id',)

    def short_review(self, obj):
        return obj.mini_review[:60] + '...' if len(obj.mini_review) > 60 else obj.mini_review
    short_review.short_description = 'Review'

    def flag_count(self, obj):
        return obj.flagged_by.count()
    flag_count.short_description = 'Flags'


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_date', 'collections')
    search_fields = ('title',)
    ordering = ('title',)


@admin.register(FilmList)
class FilmListAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner')
    search_fields = ('title', 'owner__username')


class UnmatchedFilter(admin.SimpleListFilter):
    title = 'match status'
    parameter_name = 'matched'

    def lookups(self, request, model_admin):
        return (
            ('no', 'Unmatched'),
            ('yes', 'Matched'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'no':
            return queryset.filter(film__isnull=True)
        if self.value() == 'yes':
            return queryset.filter(film__isnull=False)


@admin.register(PCCScreening)
class PCCScreeningAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'film', 'hidden')
    list_editable = ('film', 'hidden')
    list_filter = ('hidden', UnmatchedFilter)
    search_fields = ('title',)
    autocomplete_fields = ('film',)
    ordering = ('title',)
