from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Appointment,
    ClinicalHistoryEntry,
    DentalRecord,
    OdontogramEntry,
    PatientAttachment,
    Patient,
)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "cpf", "phone", "birth_date", "created_at")
    list_filter = ("created_at",)
    search_fields = ("full_name", "cpf", "phone")
    readonly_fields = ("created_at",)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "patient_link",
        "date_time",
        "end_time_display",
        "duration_minutes",
        "treatment",
        "status",
        "created_at",
    )
    list_filter = ("status", "date_time", "duration_minutes")
    search_fields = ("patient__full_name", "patient__cpf", "treatment")
    readonly_fields = ("created_at", "created_by", "updated_by")

    @admin.display(description="Paciente")
    def patient_link(self, obj):
        url = reverse("admin:app_patient_change", args=[obj.patient_id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)

    @admin.display(description="Termino")
    def end_time_display(self, obj):
        return obj.end_time.strftime("%d/%m/%Y %H:%M")

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DentalRecord)
class DentalRecordAdmin(admin.ModelAdmin):
    list_display = ("patient_link", "updated_at")
    search_fields = ("patient__full_name", "chief_complaint", "systemic_diseases")
    readonly_fields = ("updated_at",)

    @admin.display(description="Paciente")
    def patient_link(self, obj):
        url = reverse("admin:app_patient_change", args=[obj.patient_id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)


@admin.register(OdontogramEntry)
class OdontogramEntryAdmin(admin.ModelAdmin):
    list_display = ("record", "tooth_code", "condition", "updated_at")
    list_filter = ("tooth_code",)
    search_fields = ("record__patient__full_name", "condition")
    readonly_fields = ("updated_at",)


@admin.register(ClinicalHistoryEntry)
class ClinicalHistoryEntryAdmin(admin.ModelAdmin):
    list_display = ("patient_link", "procedure_name", "professional", "performed_at")
    list_filter = ("performed_at", "professional")
    search_fields = ("patient__full_name", "procedure_name", "professional")
    readonly_fields = ("created_at", "created_by", "updated_by")

    @admin.display(description="Paciente")
    def patient_link(self, obj):
        url = reverse("admin:app_patient_change", args=[obj.patient_id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PatientAttachment)
class PatientAttachmentAdmin(admin.ModelAdmin):
    list_display = ("patient_link", "title", "uploaded_at", "uploaded_by")
    list_filter = ("uploaded_at",)
    search_fields = ("patient__full_name", "title", "description")
    readonly_fields = ("uploaded_at", "uploaded_by")

    @admin.display(description="Paciente")
    def patient_link(self, obj):
        url = reverse("admin:app_patient_change", args=[obj.patient_id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)

    def save_model(self, request, obj, form, change):
        if not change and not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
