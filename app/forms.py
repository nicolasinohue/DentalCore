from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import re

from .models import (
    Appointment,
    ClinicalHistoryEntry,
    DentalRecord,
    OdontogramEntry,
    PatientAttachment,
    Patient,
    TOOTH_CHOICES,
)


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="E-mail")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "password1", "password2")


class PatientForm(forms.ModelForm):
    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Data de nascimento",
    )

    class Meta:
        model = Patient
        fields = ["full_name", "cpf", "phone", "birth_date", "notes"]
        labels = {
            "full_name": "Nome completo",
            "cpf": "CPF",
            "phone": "Telefone",
            "notes": "Observacoes",
        }

    def clean_cpf(self):
        cpf = self.cleaned_data["cpf"]
        digits = re.sub(r"\D", "", cpf)
        if len(digits) != 11:
            raise forms.ValidationError("Informe um CPF com 11 digitos.")
        if digits == digits[0] * 11:
            raise forms.ValidationError("Informe um CPF valido.")
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        digits = re.sub(r"\D", "", phone)
        if len(digits) not in {10, 11}:
            raise forms.ValidationError("Informe um telefone com DDD.")
        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"


class AppointmentForm(forms.ModelForm):
    date_time = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
        label="Data e hora",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not getattr(self.instance, "pk", None):
            self.fields["duration_minutes"].initial = int(
                getattr(settings, "DEFAULT_APPOINTMENT_DURATION_MINUTES", 60)
            )

    class Meta:
        model = Appointment
        fields = ["patient", "date_time", "duration_minutes", "treatment", "status", "notes"]
        labels = {
            "patient": "Paciente",
            "duration_minutes": "Duracao (minutos)",
            "treatment": "Procedimento",
            "status": "Status",
            "notes": "Observacoes",
        }
        help_texts = {
            "duration_minutes": "Informe um valor entre 15 e 480 minutos.",
        }

    def clean(self):
        cleaned_data = super().clean()
        date_time = cleaned_data.get("date_time")
        duration = cleaned_data.get("duration_minutes")
        status = cleaned_data.get("status")

        if not date_time or status == Appointment.STATUS_CANCELED:
            return cleaned_data

        duration = int(duration or getattr(settings, "DEFAULT_APPOINTMENT_DURATION_MINUTES", 60))
        if duration < 15 or duration > 480:
            self.add_error("duration_minutes", "Informe uma duracao entre 15 e 480 minutos.")
            return cleaned_data

        if timezone.is_naive(date_time):
            date_time = timezone.make_aware(date_time)

        if not getattr(self.instance, "pk", None) and date_time < timezone.now():
            self.add_error("date_time", "Nao e possivel criar consulta no passado.")
            return cleaned_data

        if status == Appointment.STATUS_COMPLETED and date_time > timezone.now():
            self.add_error("status", "A consulta so pode ser concluida apos o horario agendado.")
            return cleaned_data

        new_start = date_time
        new_end = new_start + timedelta(minutes=duration)
        lookup_start = new_start - timedelta(minutes=480)

        conflicting_appointments = (
            Appointment.objects.exclude(id=getattr(self.instance, "id", None))
            .exclude(status=Appointment.STATUS_CANCELED)
            .filter(date_time__lt=new_end, date_time__gt=lookup_start)
        )

        has_conflict = any(
            appointment.date_time + timedelta(minutes=appointment.duration_minutes) > new_start
            for appointment in conflicting_appointments
        )

        if has_conflict:
            self.add_error(
                "date_time",
                "Ja existe uma consulta ativa neste intervalo. Escolha outro horario.",
            )

        return cleaned_data


class DentalRecordForm(forms.ModelForm):
    class Meta:
        model = DentalRecord
        fields = [
            "chief_complaint",
            "medical_history",
            "systemic_diseases",
            "allergies",
            "medications",
            "surgeries",
            "bleeding_disorders",
            "pregnancy",
            "blood_pressure",
            "dental_history",
            "habits",
            "treatment_plan",
        ]
        labels = {
            "chief_complaint": "Queixa principal",
            "medical_history": "Anamnese e historico medico",
            "systemic_diseases": "Doencas sistemicas",
            "allergies": "Alergias",
            "medications": "Medicacoes em uso",
            "surgeries": "Cirurgias e internacoes",
            "bleeding_disorders": "Alteracoes de sangramento",
            "pregnancy": "Gestante",
            "blood_pressure": "Pressao arterial",
            "dental_history": "Historico odontologico",
            "habits": "Habitos",
            "treatment_plan": "Plano de tratamento",
        }


class OdontogramEntryForm(forms.ModelForm):
    tooth_code = forms.ChoiceField(choices=TOOTH_CHOICES, label="Dente")

    class Meta:
        model = OdontogramEntry
        fields = ["tooth_code", "condition", "notes"]
        labels = {
            "condition": "Condicao",
            "notes": "Observacoes",
        }


class ClinicalHistoryEntryForm(forms.ModelForm):
    performed_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
        label="Data e hora",
        initial=lambda: timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
    )

    class Meta:
        model = ClinicalHistoryEntry
        fields = ["appointment", "procedure_name", "description", "professional", "performed_at"]
        labels = {
            "appointment": "Consulta relacionada",
            "procedure_name": "Procedimento",
            "description": "Descricao",
            "professional": "Profissional responsavel",
        }


class PatientAttachmentForm(forms.ModelForm):
    class Meta:
        model = PatientAttachment
        fields = ["title", "file", "description"]
        labels = {
            "title": "Titulo",
            "file": "Arquivo",
            "description": "Descricao",
        }
