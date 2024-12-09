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

	def send_invitation(self, to_user, from_user):

		if from_user != self.owner:
			raise PermissionError("You don't have permission!")

		elif to_user == self.owner:
			raise PermissionError("You're already the owner!")

		elif Invitation.objects.filter(to_user=to_user, film_list=self):
			raise PermissionError("Already invited!")

		elif from_user == self.owner:
			invitation, created = Invitation.objects.get_or_create(
				from_user=self.owner,
				to_user=to_user,
				film_list=self,
			)
			invitation.save()

	def accept_invitation(self, user):
		invitation = Invitation.objects.filter(
			film_list=self,
			to_user=user,
			accepted=False
			).first()
		if invitation:
			invitation.accepted=True
			invitation.save()
			self.guests.add(user)

	def decline_invitation(self, user):
		invitation = Invitation.objects.filter(
			film_list=self,
			to_user=user,
			accepted=False
			).first()
		if invitation:
			invitation.declined=True
			invitation.save()

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
