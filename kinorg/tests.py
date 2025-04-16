from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Film, FilmList, Addition, Invitation

User = get_user_model()

class FilmModelTest(TestCase):

    def test_create_film(self):
        film = Film.objects.create(
            title="Inception",
            year=2010,
            movie_id=1,
            poster_path="path/to/poster",
        )
        self.assertEqual(film.title, "Inception")
        self.assertEqual(film.year, 2010)
        self.assertEqual(film.movie_id, 1)
        self.assertEqual(str(film), "Inception")

class FilmListModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345', email='test@internet.com')

    def test_create_film_list(self):
        film_list = FilmList.objects.create(
            title="My Favorite Films",
            owner=self.user,
        )
        self.assertEqual(film_list.title, "My Favorite Films")
        self.assertEqual(str(film_list), "My Favorite Films")

    def test_add_film_to_list(self):
        film = Film.objects.create(
            title="Inception",
            year=2010,
            movie_id=1,
            poster_path="path/to/poster",
        )
        film_list = FilmList.objects.create(
            title="My Favorite Films",
            owner=self.user,
        )
        Addition.objects.create(
            film=film,
            film_list=film_list,
            added_by=self.user,
        )
        self.assertIn(film, film_list.films.all())

class AdditionModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345', email='test@internet.com')
        self.film = Film.objects.create(
            title="Inception",
            year=2010,
            movie_id=1,
            poster_path="path/to/poster",
        )
        self.film_list = FilmList.objects.create(
            title="My Favorite Films",
            owner=self.user,
        )

    def test_addition_unique_constraint(self):
        Addition.objects.create(
            film=self.film,
            film_list=self.film_list,
            added_by=self.user,
        )
        with self.assertRaises(Exception):
            Addition.objects.create(
                film=self.film,
                film_list=self.film_list,
                added_by=self.user,
            )

class InvitationModelTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(username='testuser1', password='12345', email='test@internet.com')
        self.user2 = User.objects.create_user(username='testuser2', password='12345', email='test@internet.com')
        self.film_list = FilmList.objects.create(
            title="My Favorite Films",
            owner=self.user1,
        )

    def test_send_invitation(self):
        invitation = Invitation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            film_list=self.film_list,
        )
        self.assertEqual(invitation.from_user, self.user1)
        self.assertEqual(invitation.to_user, self.user2)
        self.assertFalse(invitation.accepted)
        self.assertFalse(invitation.declined)

    def test_invitation_unique_constraint(self):
        Invitation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            film_list=self.film_list,
        )
        with self.assertRaises(Exception):
            Invitation.objects.create(
                from_user=self.user1,
                to_user=self.user2,
                film_list=self.film_list,
            )