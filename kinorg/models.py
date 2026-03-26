from django.db import models
from django.conf import settings

from django_sqids import SqidsField, shuffle_alphabet

class Film(models.Model):

	def __str__(self):
		return self.title

	class Meta:
		ordering = ["title"]

	title = models.CharField(
		max_length=200,
		null=False,
		blank=False,
	)

	release_date = models.DateField(
		null=False,
		unique=False,
		blank=False,
	)

	id = models.BigIntegerField(
		primary_key=True,
		editable=False,
	)

	poster_path = models.CharField(
		null=False,
		unique=False,
		blank=True,
	)

	backdrop_path = models.CharField(
		null=False,
		unique=False,
		blank=True,
	)

	overview = models.TextField(
		blank=True, 
	)
	
	genres = models.JSONField(
		default=list, 
		blank=True, 
	)
	
	embedding = models.JSONField(
		null=True, 
		blank=True, 
	)
	
	embedding_updated_at = models.DateTimeField(
		null=True, 
		blank=True
	)
	
	cast = models.JSONField(
		default=list, 
		blank=True, 
	)
	
	crew = models.JSONField(
		default=list, 
		blank=True, 
	)
	
	keywords = models.JSONField(
		default=list, 
		blank=True, 
	)
	
	runtime = models.IntegerField(
		null=True, 
		blank=True, 
	)
	
	production_companies = models.JSONField(
		default=list,
		blank=True,
	)

	production_countries = models.JSONField(
		default=list,
		blank=True,
	)

	primary_country = models.CharField(
		max_length=2,
		blank=True,
		default='',
	)

	collections = models.JSONField(
		default=list,
		blank=True,
	)

	collection_ranks = models.JSONField(
		default=dict,
		blank=True,
	)

	media_type = models.CharField(
		max_length=10,
		default='movie',
		blank=True,
	)


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

	def movie_ids(self):
		return self.films.values_list('id', flat=True)

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


class WatchedFilm(models.Model):

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['user', 'film'], 
				name="unique_watched_film_per_user")
		]
		ordering = ['-watched_at']


	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='watched_films'
	)

	film = models.ForeignKey(
		Film,
		on_delete=models.CASCADE,
		related_name='watched_by'
	)

	watched_at = models.DateTimeField(
		auto_now_add=True
	)

	stars = models.IntegerField(
		choices=[(i, i) for i in range(1, 6)],
	)

	mini_review = models.CharField(
		max_length=280,
		blank=True,
	)

	review_visible = models.BooleanField(
		default=True,
	)

	flagged_by = models.ManyToManyField(
		settings.AUTH_USER_MODEL,
		blank=True,
		related_name='flagged_reviews',
	)


class PCCScreening(models.Model):
	title = models.CharField(max_length=255)
	year = models.IntegerField(null=True, blank=True)
	pcc_url = models.URLField()
	film = models.ForeignKey(
		'Film',
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='pcc_screenings',
	)
	hidden = models.BooleanField(default=False)

	def __str__(self):
		return f"PCC: {self.title} ({self.year})"


class LikedFilm(models.Model):

	class Meta:
		unique_together = ('user', 'tmdb_id')

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='liked_films',
	)

	tmdb_id = models.BigIntegerField()

	title = models.CharField(max_length=200, blank=True)

	poster_path = models.CharField(max_length=200, blank=True)

	liked_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.user} likes {self.title}"


