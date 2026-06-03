from datetime import timedelta

from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone


TOOTH_CODES = [
    "18", "17", "16", "15", "14", "13", "12", "11",
    "21", "22", "23", "24", "25", "26", "27", "28",
    "48", "47", "46", "45", "44", "43", "42", "41",
    "31", "32", "33", "34", "35", "36", "37", "38",
]

TOOTH_CHOICES = [(code, code) for code in TOOTH_CODES]


class Patient(models.Model):
    full_name = models.CharField(max_length=120)
    cpf = models.CharField(max_length=14, unique=True)
    phone = models.CharField(max_length=20)
    birth_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self) -> str:
        return self.full_name


class Appointment(models.Model):
    STATUS_SCHEDULED = "agendado"
    STATUS_COMPLETED = "concluido"
    STATUS_CANCELED = "cancelado"

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Agendado"),
        (STATUS_COMPLETED, "Concluido"),
        (STATUS_CANCELED, "Cancelado"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    date_time = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(15), MaxValueValidator(480)],
    )
    treatment = models.CharField(max_length=150)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_appointments",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_appointments",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["date_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["date_time"],
                condition=~models.Q(status="cancelado"),
                name="unique_active_appointment_datetime",
            )
        ]

    def __str__(self) -> str:
        return f"{self.patient.full_name} - {self.date_time:%d/%m/%Y %H:%M}"

    @property
    def end_time(self):
        return self.date_time + timedelta(minutes=self.duration_minutes)


class DentalRecord(models.Model):
    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        related_name="dental_record",
    )
    chief_complaint = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    systemic_diseases = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    medications = models.TextField(blank=True)
    surgeries = models.TextField(blank=True)
    bleeding_disorders = models.TextField(blank=True)
    pregnancy = models.CharField(max_length=120, blank=True)
    blood_pressure = models.CharField(max_length=40, blank=True)
    dental_history = models.TextField(blank=True)
    habits = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prontuario odontologico"
        verbose_name_plural = "Prontuarios odontologicos"

    def __str__(self) -> str:
        return f"Prontuario de {self.patient.full_name}"


class OdontogramEntry(models.Model):
    record = models.ForeignKey(
        DentalRecord,
        on_delete=models.CASCADE,
        related_name="odontogram_entries",
    )
    tooth_code = models.CharField(max_length=3, choices=TOOTH_CHOICES)
    condition = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("record", "tooth_code")
        ordering = ["tooth_code"]
        verbose_name = "Entrada de odontograma"
        verbose_name_plural = "Entradas de odontograma"

    def __str__(self) -> str:
        return f"{self.record.patient.full_name} - Dente {self.tooth_code}"


class ClinicalHistoryEntry(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="clinical_history_entries",
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        related_name="history_entries",
        blank=True,
        null=True,
    )
    procedure_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    professional = models.CharField(max_length=120, blank=True)
    performed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_clinical_history_entries",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_clinical_history_entries",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-performed_at"]
        verbose_name = "Historico clinico"
        verbose_name_plural = "Historicos clinicos"

    def __str__(self) -> str:
        return f"{self.patient.full_name} - {self.procedure_name}"


class PatientAttachment(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    title = models.CharField(max_length=150)
    file = models.FileField(upload_to="patient_attachments/%Y/%m/")
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_patient_attachments",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Anexo do paciente"
        verbose_name_plural = "Anexos dos pacientes"

    def __str__(self) -> str:
        return f"{self.patient.full_name} - {self.title}"
