from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .admin import UserCreationForm


class SiteLoginView(LoginView):
	form = AuthenticationForm
	template_name = "user_admin/login.html"
	next_page = "kinorg:home"


class SiteLogoutView(LogoutView):
	next_page = "kinorg:home"


class AddUserView(LoginRequiredMixin, UserPassesTestMixin, FormView):

	login_url = "user_admin:login"

	form_class = UserCreationForm
	success_url = "/success/"
	template_name = "user_admin/add_user.html"

	raise_exception = False

	def test_func(self):
		return self.request.user.is_admin

	def form_valid(self, form):
		form.save()
		return super().form_valid(form)



def success_page(request):
	return HttpResponse("success")