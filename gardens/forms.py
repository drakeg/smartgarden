from django import forms
from .models import Garden, Pod, PodNote
from .models import GlobalNote
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


class RegistrationForm(UserCreationForm):
    """User registration form with email and basic uniqueness validation."""
    email = forms.EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(self)


def _apply_bootstrap_classes(form: forms.BaseForm) -> None:
    """Add Bootstrap classes to common widgets in a form instance."""
    for name, field in form.fields.items():
        widget = field.widget
        existing = widget.attrs.get("class", "")
        # Selects use form-select in Bootstrap 5
        if isinstance(widget, (forms.Select, forms.SelectMultiple)):
            cls = "form-select"
        else:
            cls = "form-control"
        # Preserve any existing classes
        widget.attrs["class"] = (existing + " " + cls).strip()

class GardenForm(forms.ModelForm):
    class Meta:
        model = Garden
        fields = ["name", "device_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(self)

class PodForm(forms.ModelForm):
    class Meta:
        model = Pod
        fields = ["plant_name", "planted_at", "status"]
        widgets = {
            "planted_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(self)

class PodNoteForm(forms.ModelForm):
    class Meta:
        model = PodNote
        fields = ["note", "photo"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(self)


class GlobalNoteForm(forms.ModelForm):
    class Meta:
        model = GlobalNote
        fields = ["title", "note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(self)

