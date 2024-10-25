from django.db import models
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager, AbstractUser

# updated user settings

class SiteUserManager(BaseUserManager):
	def create_user(self, username, email, password=None):
		"""
		Creates and saves a User with the given username, email and password.
		"""
		if not email:
			raise ValueError("Users must have an email address")

		user = self.model(
			username=username,
			email=self.normalize_email(email),
		)

		user.set_password(password)
		user.save()
		return user

	def create_superuser(self, username, email, password=None):
		"""
		Creates and saves a superuser with the given username, email and password.
		"""
		user = self.create_user(
			username,
			email,
			password=password,
		)
		user.is_admin = True
		user.save()
		return user


class SiteUser(AbstractUser):

	username = models.CharField(
		verbose_name="Username",
		max_length=40, 
		unique=True,
		blank=False,
	)

	email = models.EmailField(
		verbose_name="email address",
		max_length=255,
		unique=False,
		blank=False,
	)

	is_active = models.BooleanField(
		default=True,
	)

	is_admin = models.BooleanField(
		default=False,
	)

	objects = SiteUserManager()

	USERNAME_FIELD = "username"
	REQUIRED_FIELDS = ["email"]

	class Meta:
		ordering = ["username"]

	def __str__(self):
		return self.username

	def has_perm(self, perm, obj=None):
		# "Does the user have a specific permission?"
		# Simplest possible answer: Yes, always
		return True

	def has_module_perms(self, app_label):
		# "Does the user have permissions to view the app `app_label`?"
		# Simplest possible answer: Yes, always
		return True

	@property
	def is_staff(self):
		# "Is the user a member of staff?"
		# Simplest possible answer: All admins are staff
		return self.is_admin