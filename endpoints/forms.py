from django import forms
from .models import Contact, Product

#class EmailForm(forms.Form):
#	name = forms.CharField(required=False)
#	email = forms.EmailField()

class ProductForm(forms.ModelForm):
	class Meta:
		model = Product

class ContactForm(forms.ModelForm):
	class Meta:
		model = Contact
