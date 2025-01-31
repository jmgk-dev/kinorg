from django import forms
from .models import Film, FilmList

class AddFilmForm(forms.Form):
	film_lists = forms.ModelMultipleChoiceField(
		queryset = FilmList.objects.none(),
		widget=forms.CheckboxSelectMultiple,
		required=True,
		label="Select Film Lists"
		)

	def __init__(self, *args, **kwargs):
		user = kwargs.pop('user')
		super(AddFilmForm, self).__init__(*args, **kwargs)

		if user:
			owned_lists = FilmList.objects.filter(owner=user)
			guest_lists = user.guestlists.all()
			self.fields['film_lists'].queryset = owned_lists | guest_lists