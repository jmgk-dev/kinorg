"""
Kinorg test suite.

Run with: python manage.py test kinorg
"""
import json
from datetime import date

from django.test import TestCase, Client
from django.urls import reverse

from user_admin.models import SiteUser
from kinorg.models import (
    Film, FilmList, Addition, Invitation,
    WatchedFilm, LikedFilm, WatchlistItem, PCCScreening,
)
from kinorg.views import (
    _get_director, _to_str_set, send_invitation,
    accept_invitation, decline_invitation,
    _build_genre_list, _filter_films_by_genre, _build_country_map,
    films_in_collection, get_similar_films,
)
from kinorg.templatetags.kinorg_extras import film_director, key_crew, country_abbr


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

_film_counter = 0


def make_film(tmdb_id=None, title="Test Film", year=2000, genres=None,
              crew=None, cast=None, keywords=None, production_countries=None,
              primary_country='US', collections=None, collection_ranks=None,
              poster_path='/poster.jpg'):
    """Create a Film instance with sensible defaults."""
    global _film_counter
    _film_counter += 1
    if tmdb_id is None:
        tmdb_id = 900000 + _film_counter

    return Film.objects.create(
        id=tmdb_id,
        title=title,
        release_date=date(year, 1, 1),
        poster_path=poster_path,
        genres=genres or [],
        crew=crew or [],
        cast=cast or [],
        keywords=keywords or [],
        production_countries=production_countries or [],
        primary_country=primary_country,
        collections=collections or [],
        collection_ranks=collection_ranks or {},
    )


def make_user(username="alice", password="testpass123"):
    return SiteUser.objects.create_user(username=username, email=f"{username}@example.com", password=password)


def make_list(owner, title="My List", archived=False):
    return FilmList.objects.create(owner=owner, title=title, archived=archived)


def make_watched(user, film, stars=None, mini_review='', review_visible=True):
    return WatchedFilm.objects.create(
        user=user, film=film, stars=stars,
        mini_review=mini_review, review_visible=review_visible,
    )


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class GetDirectorTests(TestCase):
    """_get_director extracts the first Director from a crew list."""

    def test_empty_returns_empty_string(self):
        self.assertEqual(_get_director(None), '')
        self.assertEqual(_get_director([]), '')

    def test_full_tmdb_dict(self):
        crew = [
            {'id': 1, 'name': 'Jane Campion', 'job': 'Director'},
            {'id': 2, 'name': 'Other Person', 'job': 'Producer'},
        ]
        self.assertEqual(_get_director(crew), 'Jane Campion')

    def test_minimal_dict_without_id(self):
        # build_defaults format — no 'id' key
        crew = [{'name': 'Akira Kurosawa', 'job': 'Director'}]
        self.assertEqual(_get_director(crew), 'Akira Kurosawa')

    def test_returns_first_director_only(self):
        crew = [
            {'name': 'Director A', 'job': 'Director'},
            {'name': 'Director B', 'job': 'Director'},
        ]
        self.assertEqual(_get_director(crew), 'Director A')

    def test_no_director_in_crew(self):
        crew = [{'id': 1, 'name': 'Bob', 'job': 'Producer'}]
        self.assertEqual(_get_director(crew), '')

    def test_raw_json_string_input(self):
        crew = json.dumps([{'name': 'Orson Welles', 'job': 'Director'}])
        self.assertEqual(_get_director(crew), 'Orson Welles')

    def test_invalid_json_string_returns_empty(self):
        self.assertEqual(_get_director("not json"), '')


class ToStrSetTests(TestCase):
    """_to_str_set converts mixed JSONFields into a set of name strings."""

    def test_plain_strings(self):
        self.assertEqual(_to_str_set(['Drama', 'Thriller']), {'Drama', 'Thriller'})

    def test_dicts(self):
        lst = [{'name': 'Drama'}, {'name': 'Thriller'}]
        self.assertEqual(_to_str_set(lst), {'Drama', 'Thriller'})

    def test_mixed(self):
        lst = ['Drama', {'name': 'Thriller'}]
        self.assertEqual(_to_str_set(lst), {'Drama', 'Thriller'})

    def test_none_returns_empty_set(self):
        self.assertEqual(_to_str_set(None), set())

    def test_custom_key(self):
        lst = [{'iso_3166_1': 'US'}, {'iso_3166_1': 'GB'}]
        self.assertEqual(_to_str_set(lst, key='iso_3166_1'), {'US', 'GB'})

    def test_dict_missing_key_is_skipped(self):
        lst = [{'name': 'Drama'}, {'other': 'x'}]
        self.assertEqual(_to_str_set(lst), {'Drama'})


# ---------------------------------------------------------------------------
# Template tag tests
# ---------------------------------------------------------------------------

class FilmDirectorTagTests(TestCase):
    """film_director templatetag extracts director name from crew JSONField."""

    def test_returns_director_name(self):
        crew = [{'id': 1, 'name': 'Ingmar Bergman', 'job': 'Director'}]
        self.assertEqual(film_director(crew), 'Ingmar Bergman')

    def test_returns_empty_when_no_director(self):
        crew = [{'id': 2, 'name': 'Bob', 'job': 'Producer'}]
        self.assertEqual(film_director(crew), '')

    def test_handles_none(self):
        self.assertEqual(film_director(None), '')

    def test_handles_raw_json_string(self):
        crew = json.dumps([{'name': 'Andrei Tarkovsky', 'job': 'Director'}])
        self.assertEqual(film_director(crew), 'Andrei Tarkovsky')


class KeyCrewTagTests(TestCase):
    """key_crew templatetag filters crew to important roles, excludes those without id."""

    def _crew(self):
        return [
            {'id': 1, 'name': 'Jane Campion', 'job': 'Director'},
            {'id': 2, 'name': 'Alice', 'job': 'Producer'},
            {'id': 3, 'name': 'Bob', 'job': 'Caterer'},          # not in KEY_CREW_JOBS
            {'name': 'No ID Guy', 'job': 'Director'},             # missing id
            {'id': 4, 'name': 'Charlie', 'job': 'Editor'},
        ]

    def test_filters_to_key_roles(self):
        result = key_crew(self._crew())
        jobs = [m['job'] for m in result]
        self.assertIn('Director', jobs)
        self.assertIn('Producer', jobs)
        self.assertIn('Editor', jobs)
        self.assertNotIn('Caterer', jobs)

    def test_excludes_members_without_id(self):
        result = key_crew(self._crew())
        names = [m['name'] for m in result]
        self.assertNotIn('No ID Guy', names)

    def test_director_comes_first(self):
        result = key_crew(self._crew())
        self.assertEqual(result[0]['job'], 'Director')

    def test_empty_input(self):
        self.assertEqual(key_crew([]), [])
        self.assertEqual(key_crew(None), [])

    def test_deduplicates_by_id_and_job(self):
        crew = [
            {'id': 1, 'name': 'Jane', 'job': 'Director'},
            {'id': 1, 'name': 'Jane', 'job': 'Director'},
        ]
        self.assertEqual(len(key_crew(crew)), 1)


class CountryAbbrTagTests(TestCase):
    def test_known_country(self):
        self.assertEqual(country_abbr('United Kingdom'), 'UK')
        self.assertEqual(country_abbr('United States of America'), 'USA')

    def test_unknown_country_passthrough(self):
        self.assertEqual(country_abbr('France'), 'France')


# ---------------------------------------------------------------------------
# Collection / genre / country filter helper tests
# ---------------------------------------------------------------------------

class CollectionFilterTests(TestCase):
    def setUp(self):
        self.film_a = make_film(title="Film A", collections=['tspdt_1000'], collection_ranks={'tspdt_1000': 1})
        self.film_b = make_film(title="Film B", collections=['sight_and_sound_2022'])
        self.film_c = make_film(title="Film C", collections=[])

    def test_films_in_collection_returns_correct_films(self):
        qs = films_in_collection('tspdt_1000')
        self.assertIn(self.film_a, qs)
        self.assertNotIn(self.film_b, qs)
        self.assertNotIn(self.film_c, qs)

    def test_films_in_collection_multiple_tags(self):
        qs = films_in_collection('sight_and_sound_2022')
        self.assertIn(self.film_b, qs)
        self.assertNotIn(self.film_a, qs)


class GenreFilterTests(TestCase):
    def setUp(self):
        self.drama = make_film(title="Drama Film", genres=[{'id': 18, 'name': 'Drama'}])
        self.thriller = make_film(title="Thriller Film", genres=[{'id': 53, 'name': 'Thriller'}])
        self.both = make_film(title="Drama Thriller", genres=[{'id': 18, 'name': 'Drama'}, {'id': 53, 'name': 'Thriller'}])

    def test_filter_by_genre(self):
        qs = _filter_films_by_genre(Film.objects.all(), 'Drama')
        self.assertIn(self.drama, qs)
        self.assertIn(self.both, qs)
        self.assertNotIn(self.thriller, qs)

    def test_build_genre_list(self):
        genres = _build_genre_list(Film.objects.all())
        self.assertIn('Drama', genres)
        self.assertIn('Thriller', genres)
        self.assertEqual(sorted(genres), genres)  # sorted alphabetically

    def test_genre_list_no_plain_strings(self):
        # Plain string genres (minimal format) should not appear — only dicts with 'name'
        make_film(title="Minimal", genres=['Action'])
        genres = _build_genre_list(Film.objects.all())
        self.assertNotIn('Action', genres)


class CountryMapTests(TestCase):
    def setUp(self):
        self.us_film = make_film(title="US Film", primary_country='US')
        self.gb_film = make_film(title="UK Film", primary_country='GB')
        make_film(title="No Country", primary_country='')

    def test_builds_sorted_country_map(self):
        countries = _build_country_map(Film.objects.all())
        codes = [c[0] for c in countries]
        self.assertIn('US', codes)
        self.assertIn('GB', codes)
        self.assertNotIn('', codes)

    def test_names_are_resolved(self):
        countries = _build_country_map(Film.objects.all())
        name_map = {code: name for code, name in countries}
        self.assertEqual(name_map['US'], 'USA')
        self.assertEqual(name_map['GB'], 'UK')


# ---------------------------------------------------------------------------
# Invitation helper tests (pure Python, no HTTP)
# ---------------------------------------------------------------------------

class InvitationHelperTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.guest = make_user('guest')
        self.other = make_user('other')
        self.film_list = make_list(self.owner)

    def test_send_invitation_creates_record(self):
        send_invitation(self.film_list, self.guest, self.owner)
        self.assertTrue(
            Invitation.objects.filter(to_user=self.guest, film_list=self.film_list).exists()
        )

    def test_non_owner_cannot_invite(self):
        with self.assertRaises(PermissionError):
            send_invitation(self.film_list, self.other, self.guest)

    def test_cannot_invite_owner(self):
        with self.assertRaises(PermissionError):
            send_invitation(self.film_list, self.owner, self.owner)

    def test_duplicate_invite_raises(self):
        send_invitation(self.film_list, self.guest, self.owner)
        with self.assertRaises(PermissionError):
            send_invitation(self.film_list, self.guest, self.owner)

    def test_accept_invitation_adds_guest(self):
        send_invitation(self.film_list, self.guest, self.owner)
        accept_invitation(self.film_list, self.guest)
        inv = Invitation.objects.get(to_user=self.guest, film_list=self.film_list)
        self.assertTrue(inv.accepted)
        self.assertIn(self.guest, self.film_list.guests.all())

    def test_decline_invitation(self):
        send_invitation(self.film_list, self.guest, self.owner)
        decline_invitation(self.film_list, self.guest)
        inv = Invitation.objects.get(to_user=self.guest, film_list=self.film_list)
        self.assertTrue(inv.declined)
        self.assertNotIn(self.guest, self.film_list.guests.all())


# ---------------------------------------------------------------------------
# View tests — base class with auth helpers
# ---------------------------------------------------------------------------

class LoggedInTestCase(TestCase):
    def setUp(self):
        self.user = make_user('testuser')
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')


# ---------------------------------------------------------------------------
# FilmDetail view tests
# ---------------------------------------------------------------------------

class FilmDetailViewTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film = make_film(
            tmdb_id=12345,
            title="Citizen Kane",
            year=1941,
            crew=[{'id': 10, 'name': 'Orson Welles', 'job': 'Director'}],
            genres=[{'id': 18, 'name': 'Drama'}],
            production_countries=['US'],
        )

    def _url(self):
        return reverse('kinorg:film_detail', kwargs={'id': self.film.id})

    def test_loads_from_db(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['film'], self.film)

    def test_directors_in_context(self):
        response = self.client.get(self._url())
        directors = response.context['directors']
        self.assertEqual(len(directors), 1)
        self.assertEqual(directors[0]['name'], 'Orson Welles')

    def test_production_countries_resolved(self):
        response = self.client.get(self._url())
        countries = response.context['production_countries']
        self.assertEqual(len(countries), 1)
        self.assertEqual(countries[0]['iso_3166_1'], 'US')
        self.assertEqual(countries[0]['name'], 'USA')

    def test_production_countries_legacy_dict_format(self):
        # Older records stored as dicts, not ISO strings
        self.film.production_countries = [{'iso_3166_1': 'GB', 'name': 'United Kingdom'}]
        self.film.save()
        response = self.client.get(self._url())
        countries = response.context['production_countries']
        self.assertEqual(countries[0]['iso_3166_1'], 'GB')
        self.assertEqual(countries[0]['name'], 'UK')  # resolved via COUNTRY_ISO

    def test_watched_is_none_when_not_logged_as_watched(self):
        response = self.client.get(self._url())
        self.assertIsNone(response.context['watched'])

    def test_watched_is_populated_when_user_has_record(self):
        make_watched(self.user, self.film, stars=4)
        response = self.client.get(self._url())
        self.assertIsNotNone(response.context['watched'])
        self.assertEqual(response.context['watched'].stars, 4)

    def test_is_liked_false_by_default(self):
        response = self.client.get(self._url())
        self.assertFalse(response.context['is_liked'])

    def test_is_liked_true_when_liked(self):
        LikedFilm.objects.create(user=self.user, tmdb_id=self.film.id, title=self.film.title)
        response = self.client.get(self._url())
        self.assertTrue(response.context['is_liked'])

    def test_in_watchlist_false_by_default(self):
        response = self.client.get(self._url())
        self.assertFalse(response.context['in_watchlist'])

    def test_in_watchlist_true_when_added(self):
        WatchlistItem.objects.create(user=self.user, film=self.film)
        response = self.client.get(self._url())
        self.assertTrue(response.context['in_watchlist'])

    def test_similar_films_from_precomputed_ids(self):
        similar = make_film(title="Similar Film")
        self.film.similar_film_ids = [similar.id]
        self.film.save()
        response = self.client.get(self._url())
        self.assertIn(similar, response.context['similar_films'])

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self._url())
        self.assertNotEqual(response.status_code, 200)

    def test_minimal_crew_no_id_does_not_crash(self):
        # build_defaults format — crew dicts without 'id'
        self.film.crew = [{'name': 'Orson Welles', 'job': 'Director'}]
        self.film.cast = ['Actor Name']  # plain string cast
        self.film.save()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_first_visit_imports_from_tmdb(self):
        """Film not yet in DB triggers _import_film_from_tmdb; returned object must have
        release_date as a date (not a string) so .year doesn't raise AttributeError."""
        from unittest.mock import patch
        from datetime import date

        tmdb_id = 99999
        self.assertFalse(Film.objects.filter(id=tmdb_id).exists())

        fake_tmdb_response = {
            'id': tmdb_id,
            'title': 'New Film',
            'release_date': '2010-06-15',
            'poster_path': '/p.jpg',
            'backdrop_path': '',
            'overview': 'A film.',
            'tagline': '',
            'runtime': 100,
            'genres': [{'id': 18, 'name': 'Drama'}],
            'credits': {'cast': [], 'crew': []},
            'keywords': {'keywords': []},
            'production_companies': [],
            'production_countries': [{'iso_3166_1': 'US', 'name': 'United States of America'}],
            'videos': {'results': []},
            'watch/providers': {'results': {}},
        }

        url = reverse('kinorg:film_detail', kwargs={'id': tmdb_id})
        with patch('kinorg.views.get_tmdb_data', return_value=fake_tmdb_response):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        film = Film.objects.get(id=tmdb_id)
        self.assertIsInstance(film.release_date, date)
        self.assertEqual(film.release_date.year, 2010)
        # release_date_str on context object must also work
        self.assertEqual(response.context['film'].release_date_str, '2010-06-15')


# ---------------------------------------------------------------------------
# Toggle like / watched / watchlist
# ---------------------------------------------------------------------------

class ToggleLikeTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film = make_film(tmdb_id=55555, title="Like Test")
        self.url = reverse('kinorg:toggle_like', kwargs={'tmdb_id': self.film.id})

    def test_like_creates_record(self):
        response = self.client.post(self.url, {'title': self.film.title})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(LikedFilm.objects.filter(user=self.user, tmdb_id=self.film.id).exists())
        data = json.loads(response.content)
        self.assertTrue(data['liked'])

    def test_unlike_deletes_record(self):
        LikedFilm.objects.create(user=self.user, tmdb_id=self.film.id, title=self.film.title)
        response = self.client.post(self.url, {'title': self.film.title})
        self.assertFalse(LikedFilm.objects.filter(user=self.user, tmdb_id=self.film.id).exists())
        data = json.loads(response.content)
        self.assertFalse(data['liked'])

    def test_get_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)


class ToggleWatchedTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film = make_film(tmdb_id=66666, title="Watched Test")
        self.url = reverse('kinorg:toggle_watched', kwargs={'tmdb_id': self.film.id})

    def test_mark_as_watched_creates_record(self):
        response = self.client.post(self.url, {'title': self.film.title, 'release_date': '2000-01-01'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(WatchedFilm.objects.filter(user=self.user, film=self.film).exists())
        self.assertTrue(json.loads(response.content)['watched'])

    def test_toggle_off_deletes_record(self):
        make_watched(self.user, self.film)
        response = self.client.post(self.url)
        self.assertFalse(WatchedFilm.objects.filter(user=self.user, film=self.film).exists())
        self.assertFalse(json.loads(response.content)['watched'])

    def test_creates_film_stub_if_not_in_db(self):
        Film.objects.filter(id=self.film.id).delete()
        self.client.post(self.url, {'title': 'New Film', 'release_date': '2000-01-01'})
        self.assertTrue(Film.objects.filter(id=self.film.id).exists())


class ToggleWatchlistTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film = make_film(tmdb_id=77777, title="Watchlist Test")
        self.url = reverse('kinorg:toggle_watchlist', kwargs={'tmdb_id': self.film.id})

    def test_add_to_watchlist(self):
        response = self.client.post(self.url, {'title': self.film.title, 'release_date': '2000-01-01'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(WatchlistItem.objects.filter(user=self.user, film=self.film).exists())
        self.assertTrue(json.loads(response.content)['in_watchlist'])

    def test_remove_from_watchlist(self):
        WatchlistItem.objects.create(user=self.user, film=self.film)
        response = self.client.post(self.url)
        self.assertFalse(WatchlistItem.objects.filter(user=self.user, film=self.film).exists())
        self.assertFalse(json.loads(response.content)['in_watchlist'])


# ---------------------------------------------------------------------------
# Review actions
# ---------------------------------------------------------------------------

class AddReviewTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film = make_film(tmdb_id=88888, title="Review Film", year=2000)
        self.url = reverse('kinorg:add_review')

    def _post(self, stars='', mini_review='', review_visible='true'):
        return self.client.post(self.url, {
            'id': self.film.id,
            'title': self.film.title,
            'release_date': '2000-01-01',
            'poster_path': '/p.jpg',
            'backdrop_path': '',
            'overview': '',
            'runtime': '90',
            'cast': '[]',
            'crew': '[]',
            'genres': '[]',
            'keywords': '[]',
            'production_companies': '[]',
            'stars': stars,
            'mini_review': mini_review,
            'review_visible': review_visible,
        })

    def test_saves_stars(self):
        self._post(stars='4')
        watched = WatchedFilm.objects.get(user=self.user, film=self.film)
        self.assertEqual(watched.stars, 4)

    def test_saves_mini_review(self):
        self._post(mini_review='Great film!')
        watched = WatchedFilm.objects.get(user=self.user, film=self.film)
        self.assertEqual(watched.mini_review, 'Great film!')

    def test_censors_profanity(self):
        self._post(mini_review='This is shit')
        watched = WatchedFilm.objects.get(user=self.user, film=self.film)
        self.assertNotIn('shit', watched.mini_review)

    def test_private_review_saved(self):
        self._post(stars='3', review_visible='false')
        watched = WatchedFilm.objects.get(user=self.user, film=self.film)
        self.assertFalse(watched.review_visible)

    def test_empty_form_no_existing_record_does_not_create(self):
        self._post()
        self.assertFalse(WatchedFilm.objects.filter(user=self.user, film=self.film).exists())

    def test_empty_stars_clears_existing_stars(self):
        make_watched(self.user, self.film, stars=5, mini_review='Good')
        self._post(stars='', mini_review='Good')
        watched = WatchedFilm.objects.get(user=self.user, film=self.film)
        self.assertIsNone(watched.stars)

    def test_updates_existing_record(self):
        make_watched(self.user, self.film, stars=3)
        self._post(stars='5', mini_review='Better now')
        watched = WatchedFilm.objects.get(user=self.user, film=self.film)
        self.assertEqual(watched.stars, 5)
        self.assertEqual(watched.mini_review, 'Better now')

    def test_get_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)


class RemoveReviewTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film = make_film(tmdb_id=99991, title="Remove Review Film")
        self.url = reverse('kinorg:remove_review')

    def test_clears_mini_review_keeps_stars(self):
        make_watched(self.user, self.film, stars=4, mini_review='A review')
        self.client.post(self.url, {'id': self.film.id})
        watched = WatchedFilm.objects.get(user=self.user, film=self.film)
        self.assertEqual(watched.mini_review, '')
        self.assertEqual(watched.stars, 4)  # stars preserved
        # Record not deleted
        self.assertTrue(WatchedFilm.objects.filter(user=self.user, film=self.film).exists())

    def test_get_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)


class ToggleReviewPrivateTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film = make_film(tmdb_id=99992, title="Privacy Film")
        self.url = reverse('kinorg:toggle_review_private')

    def test_sets_review_invisible(self):
        make_watched(self.user, self.film, review_visible=True)
        response = self.client.post(self.url, {'film_id': self.film.id, 'review_visible': 'false'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['review_visible'])
        watched = WatchedFilm.objects.get(user=self.user, film=self.film)
        self.assertFalse(watched.review_visible)

    def test_sets_review_visible(self):
        make_watched(self.user, self.film, review_visible=False)
        response = self.client.post(self.url, {'film_id': self.film.id, 'review_visible': 'true'})
        data = json.loads(response.content)
        self.assertTrue(data['review_visible'])

    def test_no_watched_record_returns_desired_state(self):
        response = self.client.post(self.url, {'film_id': self.film.id, 'review_visible': 'false'})
        data = json.loads(response.content)
        self.assertFalse(data['review_visible'])
        # Should not have created a record
        self.assertFalse(WatchedFilm.objects.filter(user=self.user, film=self.film).exists())

    def test_get_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# Flag review
# ---------------------------------------------------------------------------

class FlagReviewTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.other_user = make_user('other')
        self.film = make_film(tmdb_id=99993, title="Flag Film")
        self.review = make_watched(self.other_user, self.film, mini_review='Watch this')

    def _url(self, review_id):
        return reverse('kinorg:flag_review', kwargs={'review_id': review_id})

    def test_flag_adds_user_to_flagged_by(self):
        response = self.client.post(self._url(self.review.id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, self.review.flagged_by.all())
        self.assertTrue(json.loads(response.content)['flagged'])

    def test_unflag_removes_user(self):
        self.review.flagged_by.add(self.user)
        response = self.client.post(self._url(self.review.id))
        self.assertNotIn(self.user, self.review.flagged_by.all())
        self.assertFalse(json.loads(response.content)['flagged'])

    def test_cannot_flag_own_review(self):
        own_review = make_watched(self.user, make_film(tmdb_id=99994, title='Own Film'), mini_review='Mine')
        response = self.client.post(self._url(own_review.id))
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_review_returns_404(self):
        response = self.client.post(self._url(9999999))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Add/remove film from list
# ---------------------------------------------------------------------------

class AddFilmTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film_list = make_list(self.user)
        self.url = reverse('kinorg:add_film')

    def _post(self, tmdb_id, list_id):
        return self.client.post(self.url, {
            'id': tmdb_id,
            'title': 'Test Film',
            'release_date': '2000-01-01',
            'poster_path': '/p.jpg',
            'backdrop_path': '',
            'overview': '',
            'runtime': '90',
            'cast': '[]',
            'crew': '[]',
            'genres': '[]',
            'keywords': '[]',
            'production_companies': '[]',
            'production_countries': '',
            'list_id': list_id,
        })

    def test_creates_film_and_addition(self):
        self._post(11111, self.film_list.id)
        self.assertTrue(Film.objects.filter(id=11111).exists())
        self.assertTrue(Addition.objects.filter(film_id=11111, film_list=self.film_list).exists())

    def test_does_not_duplicate_addition(self):
        self._post(11112, self.film_list.id)
        self._post(11112, self.film_list.id)
        self.assertEqual(Addition.objects.filter(film_id=11112, film_list=self.film_list).count(), 1)

    def test_get_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)


class RemoveFilmTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film = make_film(tmdb_id=22222, title="Remove Me")
        self.film_list = make_list(self.user)
        Addition.objects.create(film=self.film, film_list=self.film_list, added_by=self.user)
        self.url = reverse('kinorg:remove_film')

    def test_removes_film_from_list(self):
        self.client.post(self.url, {'id': self.film.id, 'list_id': self.film_list.id})
        self.assertFalse(Addition.objects.filter(film=self.film, film_list=self.film_list).exists())

    def test_get_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# Archive list
# ---------------------------------------------------------------------------

class ArchiveListTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film_list = make_list(self.user)
        self.url = reverse('kinorg:toggle_archive_list', kwargs={'slug': self.film_list.sqid})

    def test_archives_list(self):
        self.client.post(self.url)
        self.film_list.refresh_from_db()
        self.assertTrue(self.film_list.archived)

    def test_unarchives_list(self):
        self.film_list.archived = True
        self.film_list.save()
        self.client.post(self.url)
        self.film_list.refresh_from_db()
        self.assertFalse(self.film_list.archived)

    def test_non_owner_cannot_archive(self):
        other = make_user('intruder')
        other_client = Client()
        other_client.login(username='intruder', password='testpass123')
        response = other_client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.film_list.refresh_from_db()
        self.assertFalse(self.film_list.archived)


# ---------------------------------------------------------------------------
# List access control
# ---------------------------------------------------------------------------

class ListAccessTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.owner = make_user('listowner')
        self.film_list = make_list(self.owner)

    def test_owner_can_access_list(self):
        owner_client = Client()
        owner_client.login(username='listowner', password='testpass123')
        url = reverse('kinorg:list', kwargs={'slug': self.film_list.sqid})
        response = owner_client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_non_member_redirected_to_no_access(self):
        url = reverse('kinorg:list', kwargs={'slug': self.film_list.sqid})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('kinorg:no_access'))

    def test_guest_can_access_list(self):
        self.film_list.guests.add(self.user)
        url = reverse('kinorg:list', kwargs={'slug': self.film_list.sqid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Invite-related HTTP endpoints
# ---------------------------------------------------------------------------

class InviteGuestViewTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.film_list = make_list(self.user)
        self.invitee = make_user('invitee')
        self.url = reverse('kinorg:invite_guest')

    def test_owner_can_invite(self):
        response = self.client.post(self.url, {
            'list_id': self.film_list.id,
            'username': 'invitee',
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(Invitation.objects.filter(to_user=self.invitee, film_list=self.film_list).exists())

    def test_cannot_invite_nonexistent_user(self):
        response = self.client.post(self.url, {
            'list_id': self.film_list.id,
            'username': 'nobody',
        })
        data = json.loads(response.content)
        self.assertFalse(data['success'])


# ---------------------------------------------------------------------------
# My Lists page
# ---------------------------------------------------------------------------

class MyListsViewTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('kinorg:my_lists')

    def test_shows_owned_lists(self):
        lst = make_list(self.user, title="My Great List")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(lst, response.context['my_lists'])

    def test_archived_lists_not_in_my_lists(self):
        active = make_list(self.user, title="Active")
        archived = make_list(self.user, title="Archived", archived=True)
        response = self.client.get(self.url)
        self.assertIn(active, response.context['my_lists'])
        self.assertNotIn(archived, response.context['my_lists'])
        self.assertIn(archived, response.context['archived_lists'])

    def test_guest_lists_shown(self):
        owner = make_user('another_owner')
        shared = make_list(owner, title="Shared With Me")
        shared.guests.add(self.user)
        response = self.client.get(self.url)
        self.assertIn(shared, response.context['guest_lists'])


# ---------------------------------------------------------------------------
# Similar films scoring
# ---------------------------------------------------------------------------

class SimilarFilmsTests(TestCase):
    def setUp(self):
        self.target = make_film(
            tmdb_id=40001,
            title="Target Film",
            year=1975,
            genres=[{'id': 18, 'name': 'Drama'}],
            crew=[{'id': 1, 'name': 'Spielberg', 'job': 'Director'}],
            keywords=[{'id': 100, 'name': 'war'}],
            production_countries=['US'],
        )
        # Very similar
        self.similar = make_film(
            tmdb_id=40002,
            title="Similar Film",
            year=1977,
            genres=[{'id': 18, 'name': 'Drama'}],
            crew=[{'id': 1, 'name': 'Spielberg', 'job': 'Director'}],
            keywords=[{'id': 100, 'name': 'war'}],
            production_countries=['US'],
        )
        # Not similar at all
        self.dissimilar = make_film(
            tmdb_id=40003,
            title="Dissimilar Film",
            year=2020,
            genres=[{'id': 35, 'name': 'Comedy'}],
            production_countries=['JP'],
        )

    def test_similar_film_scores_higher_than_dissimilar(self):
        results = get_similar_films(self.target.id, self.target)
        result_ids = [f.id for f in results]
        similar_pos = result_ids.index(self.similar.id) if self.similar.id in result_ids else 999
        dissimilar_pos = result_ids.index(self.dissimilar.id) if self.dissimilar.id in result_ids else 999
        self.assertLess(similar_pos, dissimilar_pos)

    def test_excludes_self(self):
        results = get_similar_films(self.target.id, self.target)
        result_ids = [f.id for f in results]
        self.assertNotIn(self.target.id, result_ids)

    def test_excludes_films_without_poster(self):
        no_poster = make_film(tmdb_id=40004, title="No Poster", poster_path='',
                              genres=[{'id': 18, 'name': 'Drama'}])
        results = get_similar_films(self.target.id, self.target)
        result_ids = [f.id for f in results]
        self.assertNotIn(no_poster.id, result_ids)

    def test_returns_empty_for_no_film_obj(self):
        self.assertEqual(get_similar_films(99999, None), [])


# ---------------------------------------------------------------------------
# Model constraint tests
# ---------------------------------------------------------------------------

class ModelConstraintTests(TestCase):
    def setUp(self):
        self.user = make_user('constraintuser')
        self.film = make_film(tmdb_id=50001, title="Constraint Film")
        self.film_list = make_list(self.user)

    def test_unique_watched_film_per_user(self):
        from django.db import IntegrityError
        WatchedFilm.objects.create(user=self.user, film=self.film)
        with self.assertRaises(IntegrityError):
            WatchedFilm.objects.create(user=self.user, film=self.film)

    def test_unique_watchlist_item(self):
        from django.db import IntegrityError
        WatchlistItem.objects.create(user=self.user, film=self.film)
        with self.assertRaises(IntegrityError):
            WatchlistItem.objects.create(user=self.user, film=self.film)

    def test_unique_film_in_list(self):
        from django.db import IntegrityError
        Addition.objects.create(film=self.film, film_list=self.film_list, added_by=self.user)
        with self.assertRaises(IntegrityError):
            Addition.objects.create(film=self.film, film_list=self.film_list, added_by=self.user)

    def test_unique_invite_per_list(self):
        from django.db import IntegrityError
        other = make_user('invited_user')
        Invitation.objects.create(from_user=self.user, to_user=other, film_list=self.film_list)
        with self.assertRaises(IntegrityError):
            Invitation.objects.create(from_user=self.user, to_user=other, film_list=self.film_list)
