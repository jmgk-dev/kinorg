from django.db import models
from django.conf import settings

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




