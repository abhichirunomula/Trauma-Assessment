from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

from .models import Assessment


SYMPTOMS = (("sleep", "Sleep changes"), ("anxiety", "Feeling anxious or on edge"), ("low_mood", "Low mood or loss of interest"), ("concentration", "Difficulty concentrating"), ("pain", "Pain, tension, or physical discomfort"), ("energy", "Low energy or fatigue"), ("appetite", "Changes in appetite"), ("none", "None of these"))


class ChoiceAnswerForm(forms.Form):
    value = forms.ChoiceField(widget=forms.RadioSelect)

    def __init__(self, *args, choices, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].choices = choices


class SymptomsForm(forms.Form):
    symptoms = forms.MultipleChoiceField(choices=SYMPTOMS, widget=forms.CheckboxSelectMultiple)

    def clean_symptoms(self):
        symptoms = self.cleaned_data["symptoms"]
        if "none" in symptoms and len(symptoms) > 1:
            raise forms.ValidationError("Choose ‘None of these’ on its own.")
        return symptoms


class ConversationForm(forms.Form):
    message = forms.CharField(max_length=1500, strip=True)


class RegisterForm(UserCreationForm):
    username = forms.CharField(max_length=150, help_text="Use a name that does not identify you if you prefer privacy.")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "password1", "password2")


class SignInForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autocomplete": "username"}))


class AdaptiveAnswerForm(forms.Form):
    value = forms.ChoiceField(widget=forms.RadioSelect, required=False)

    def __init__(self, *args, choices, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].choices = choices
