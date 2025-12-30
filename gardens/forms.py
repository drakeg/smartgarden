from django import forms
from .models import Garden, Pod, PodNote
from .models import GlobalNote

class GardenForm(forms.ModelForm):
    class Meta:
        model = Garden
        fields = ["name", "device_type"]

class PodForm(forms.ModelForm):
    class Meta:
        model = Pod
        fields = ["plant_name", "planted_at", "status"]
        widgets = {
            "planted_at": forms.DateInput(attrs={"type": "date"}),
        }

class PodNoteForm(forms.ModelForm):
    class Meta:
        model = PodNote
        fields = ["note", "photo"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3}),
        }


class GlobalNoteForm(forms.ModelForm):
    class Meta:
        model = GlobalNote
        fields = ["title", "note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 4}),
        }

