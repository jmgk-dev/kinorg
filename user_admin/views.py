from django.shortcuts import render
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetConfirmView, PasswordResetCompleteView, PasswordResetDoneView
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .admin import UserCreationForm


class SiteLogin(LoginView):
	form = AuthenticationForm
	template_name = "user_admin/login.html"
	next_page = "kinorg:home"
	redirect_authenticated_user = True


class SiteLogout(LogoutView):
	next_page = "kinorg:home"


class AddUser(LoginRequiredMixin, UserPassesTestMixin, FormView):

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


class ResetPassword(PasswordResetView):
	template_name = 'user_admin/reset_password.html'
	email_template_name = 'user_admin/reset_password_email.html' 
	success_url = reverse_lazy('user_admin:reset_password_done')


class ResetPasswordConfirm(PasswordResetConfirmView):
	template_name = 'user_admin/reset_password_confirm.html'
	success_url = reverse_lazy('user_admin:reset_password_complete') 
	pass


class ResetPasswordComplete(PasswordResetCompleteView):
	template_name = 'user_admin/reset_password_complete.html'
	pass


class ResetPasswordDone(PasswordResetDoneView):
	template_name = 'user_admin/reset_password_done.html'




