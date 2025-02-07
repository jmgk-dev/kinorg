from django.db import models
from django.conf import settings

from django_sqids import SqidsField, shuffle_alphabet

class Film(models.Model):

	title = models.CharField(
		max_length=200,
		null=False,
		blank=False,
		)

	year = models.PositiveIntegerField(
		null=False,
		unique=False,
		blank=False,
		)

	movie_id = models.IntegerField(
		null=False,
		unique=True,
		blank=False,
		)

	poster_path = models.CharField(
		null=False,
		unique=False,
		blank=True,
		)

	def __str__(self):
		return self.title

	class Meta:
		ordering = ["title"]


class FilmList(models.Model):

	sqid = SqidsField(
		real_field_name="id",
		min_length=5, 
		unique=True,
		)

	title = models.CharField(
		max_length=200,
		null=False,
		blank=False,
		)

	films = models.ManyToManyField(
		Film,
		through="Addition",
		through_fields=("film_list", "film"),
		)

	owner = models.ForeignKey(
		settings.AUTH_USER_MODEL, 
		on_delete=models.SET_NULL,
		null=True,
		blank=False,
		)

	guests = models.ManyToManyField(
		settings.AUTH_USER_MODEL,
		related_name="guestlists",
		related_query_name="guestlist",
		)

	def __str__(self):
		return self.title

	class Meta:
		ordering = ["title"]


class Addition(models.Model):

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['film', 'film_list'], 
				name="unique_film_in_list")
		]

	film = models.ForeignKey(
		Film, 
		on_delete=models.CASCADE
		)

	film_list = models.ForeignKey(
		FilmList, 
		on_delete=models.CASCADE
		)

	date_added = models.DateField(
		auto_now_add=True
		)

	added_by = models.ForeignKey(
		settings.AUTH_USER_MODEL, 
		on_delete=models.CASCADE
		)


class Invitation(models.Model):

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['to_user', 'film_list'], 
				name="unique_invite_per_list")
		]

	from_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='sent_invitations'
		)

	to_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='received_invitations'
		)

	film_list = models.ForeignKey(
		FilmList, 
		on_delete=models.CASCADE
		)

	sent_at = models.DateTimeField(
		auto_now_add=True
		)

	accepted = models.BooleanField(
		default=False
		)

	declined = models.BooleanField(
		default=False
		)
