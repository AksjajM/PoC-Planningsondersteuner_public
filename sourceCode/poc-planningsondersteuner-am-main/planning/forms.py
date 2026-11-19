from django import forms
from .models import DefaultAvailability, Role, VacationRequest
from .services import save_default_availability


class AvailabilityExceptionNoteForm(forms.Form):
    """Valideert de verplichte toelichting bij een beschikbaarheidsafwijking."""

    note = forms.CharField(
        required=True,
        max_length=231,
        error_messages={"required": "Enter a reason before saving."},
    )

class DefaultAvailabilityForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        
        # PLON-25 review: alleen actieve rollen tonen in het formulier.
        roles = Role.objects.filter(is_active=True)
        
        for day_val, day_name in DefaultAvailability.DayOfWeek.choices:
            if day_val > 5:
                continue
            for part_val, part_name in DefaultAvailability.PartOfDay.choices:
                field_name = f"{day_val}_{part_val}"
                self.fields[field_name] = forms.ModelChoiceField(
                    queryset=roles,
                    required=True,
                    label=f"{day_name} {part_name}",
                    empty_label="---------"
                )
        existing = DefaultAvailability.objects.filter(user=self.user)
        for e in existing:
            if e.day_of_week <= 5 and e.role_id:
                self.initial[f"{e.day_of_week}_{e.part_of_day}"] = e.role_id

    def save(self):
        save_default_availability(self.user, self.cleaned_data)


class VacationRequestForm(forms.ModelForm):
    class Meta:
        model = VacationRequest
        fields = ["start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date", "style": "padding: 8px; border: 1px solid #ccc; border-radius: 4px;"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "style": "padding: 8px; border: 1px solid #ccc; border-radius: 4px;"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("Einddatum mag niet vóór de startdatum liggen.")

        return cleaned_data

