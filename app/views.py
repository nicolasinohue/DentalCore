import calendar
from collections import Counter
from datetime import datetime, timedelta
import re
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import (
    AppointmentForm,
    ClinicalHistoryEntryForm,
    DentalRecordForm,
    LoginForm,
    OdontogramEntryForm,
    PatientAttachmentForm,
    PatientForm,
    RegisterForm,
)
from .models import (
    Appointment,
    ClinicalHistoryEntry,
    DentalRecord,
    OdontogramEntry,
    PatientAttachment,
    Patient,
)
from .permissions import ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION, role_required


ODONTOGRAM_ROWS = [
    ["18", "17", "16", "15", "14", "13", "12", "11"],
    ["21", "22", "23", "24", "25", "26", "27", "28"],
    ["48", "47", "46", "45", "44", "43", "42", "41"],
    ["31", "32", "33", "34", "35", "36", "37", "38"],
]


def _ensure_history_for_completed_appointment(appointment, user):
    if appointment.status != Appointment.STATUS_COMPLETED:
        return

    ClinicalHistoryEntry.objects.get_or_create(
        appointment=appointment,
        patient=appointment.patient,
        defaults={
            "procedure_name": appointment.treatment,
            "description": appointment.notes,
            "performed_at": appointment.date_time,
            "created_by": user,
            "updated_by": user,
        },
    )


def _parse_reference_date(raw_date: str):
    if not raw_date:
        return timezone.localdate()
    try:
        return datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return timezone.localdate()


def _get_period_range(reference_date, period: str):
    if period == "day":
        start_day = reference_date
        end_day = reference_date + timedelta(days=1)
    elif period == "month":
        start_day = reference_date.replace(day=1)
        if reference_date.month == 12:
            end_day = reference_date.replace(year=reference_date.year + 1, month=1, day=1)
        else:
            end_day = reference_date.replace(month=reference_date.month + 1, day=1)
    else:
        start_day = reference_date - timedelta(days=reference_date.weekday())
        end_day = start_day + timedelta(days=7)

    start_dt = timezone.make_aware(datetime.combine(start_day, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end_day, datetime.min.time()))
    return start_day, end_day, start_dt, end_dt


def _build_agenda_days(appointments, start_day, end_day, now):
    days = []
    cursor = start_day
    while cursor < end_day:
        days.append(
            {
                "date": cursor,
                "appointments": [],
                "total": 0,
                "scheduled": 0,
                "completed": 0,
                "canceled": 0,
            }
        )
        cursor += timedelta(days=1)

    day_map = {day["date"]: day for day in days}
    next_scheduled_id = None
    for appointment in appointments:
        if appointment.status == Appointment.STATUS_SCHEDULED and appointment.end_time >= now:
            next_scheduled_id = appointment.id
            break

    for appointment in appointments:
        day = day_map.get(timezone.localtime(appointment.date_time).date())
        if not day:
            continue

        is_late = appointment.status == Appointment.STATUS_SCHEDULED and appointment.end_time < now
        is_next = appointment.id == next_scheduled_id
        day["appointments"].append(
            {
                "appointment": appointment,
                "is_late": is_late,
                "is_next": is_next,
                "start_label": timezone.localtime(appointment.date_time).strftime("%H:%M"),
                "end_label": timezone.localtime(appointment.end_time).strftime("%H:%M"),
            }
        )
        day["total"] += 1
        if appointment.status == Appointment.STATUS_SCHEDULED:
            day["scheduled"] += 1
        elif appointment.status == Appointment.STATUS_COMPLETED:
            day["completed"] += 1
        elif appointment.status == Appointment.STATUS_CANCELED:
            day["canceled"] += 1

    return days


class UserLoginView(LoginView):
    template_name = "auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = "login"


def register_view(request):
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        messages.warning(
            request,
            "Cadastro publico desativado. Solicite acesso ao administrador.",
        )
        return redirect("login")

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Conta criada com sucesso.")
            return redirect("dashboard")
    else:
        form = RegisterForm()

    return render(request, "auth/register.html", {"form": form})


@login_required
def dashboard_view(request):
    now = timezone.localtime()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_today = start_today + timedelta(days=1)
    selected_period = request.GET.get("period", "month")
    if selected_period not in {"day", "month", "year"}:
        selected_period = "month"

    if selected_period == "day":
        period_start = start_today
        period_end = end_today
        period_label = f"Dia atual - {period_start:%d/%m/%Y}"
    elif selected_period == "year":
        period_start = start_today.replace(month=1, day=1)
        period_end = period_start.replace(year=period_start.year + 1)
        period_label = f"Ano atual - {period_start:%Y}"
    else:
        period_start = start_today.replace(day=1)
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1)
        period_label = f"Mes atual - {period_start:%m/%Y}"

    total_patients = Patient.objects.count()
    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(
        date_time__gte=start_today,
        date_time__lt=end_today,
    ).count()
    period_appointments = Appointment.objects.filter(
        date_time__gte=period_start,
        date_time__lt=period_end,
    )
    period_appointments_count = period_appointments.count()
    period_canceled = period_appointments.filter(status=Appointment.STATUS_CANCELED).count()
    period_scheduled = period_appointments.filter(status=Appointment.STATUS_SCHEDULED).count()
    period_completed = period_appointments.filter(status=Appointment.STATUS_COMPLETED).count()
    cancellation_rate = (
        round((period_canceled / period_appointments_count) * 100, 1)
        if period_appointments_count
        else 0
    )
    occupied_minutes = sum(
        appointment.duration_minutes
        for appointment in period_appointments.exclude(status=Appointment.STATUS_CANCELED)
    )

    patients_with_appointments = (
        period_appointments.exclude(status=Appointment.STATUS_CANCELED)
        .values("patient_id")
        .annotate(total=Count("id"))
    )
    total_period_patients = patients_with_appointments.count()
    returning_patients = sum(1 for item in patients_with_appointments if item["total"] >= 2)
    return_rate = (
        round((returning_patients / total_period_patients) * 100, 1)
        if total_period_patients
        else 0
    )

    top_treatments = list(
        period_appointments.exclude(status=Appointment.STATUS_CANCELED)
        .values("treatment")
        .annotate(total=Count("id"))
        .order_by("-total", "treatment")[:5]
    )
    max_treatment_total = max((item["total"] for item in top_treatments), default=0)
    for item in top_treatments:
        item["percent"] = (
            round((item["total"] / max_treatment_total) * 100)
            if max_treatment_total
            else 0
        )

    treatment_minutes = {}
    for appointment in period_appointments.exclude(status=Appointment.STATUS_CANCELED):
        treatment_minutes[appointment.treatment] = (
            treatment_minutes.get(appointment.treatment, 0) + appointment.duration_minutes
        )
    top_treatment_minutes = [
        {"treatment": treatment, "minutes": minutes}
        for treatment, minutes in sorted(
            treatment_minutes.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
    ]
    max_treatment_minutes = max(
        (item["minutes"] for item in top_treatment_minutes),
        default=0,
    )
    for item in top_treatment_minutes:
        item["percent"] = (
            round((item["minutes"] / max_treatment_minutes) * 100)
            if max_treatment_minutes
            else 0
        )

    period_appointments_list = period_appointments.select_related("patient").order_by("date_time")

    context = {
        "total_patients": total_patients,
        "total_appointments": total_appointments,
        "today_appointments": today_appointments,
        "period_appointments_count": period_appointments_count,
        "period_scheduled": period_scheduled,
        "period_completed": period_completed,
        "period_canceled": period_canceled,
        "cancellation_rate": cancellation_rate,
        "occupied_minutes": occupied_minutes,
        "return_rate": return_rate,
        "top_treatments": top_treatments,
        "top_treatment_minutes": top_treatment_minutes,
        "selected_period": selected_period,
        "period_label": period_label,
        "period_appointments_list": period_appointments_list,
    }
    return render(request, "dashboard.html", context)


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def patient_list_view(request):
    search = request.GET.get("search", "").strip()
    patients = Patient.objects.all()

    if search:
        search_digits = re.sub(r"\D", "", search)
        formatted_cpf = (
            f"{search_digits[:3]}.{search_digits[3:6]}.{search_digits[6:9]}-{search_digits[9:]}"
            if len(search_digits) == 11
            else search
        )
        patients = patients.filter(
            Q(full_name__icontains=search)
            | Q(cpf__icontains=search)
            | Q(cpf__icontains=formatted_cpf)
            | Q(phone__icontains=search)
            | Q(notes__icontains=search)
        )

    paginator = Paginator(patients, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    for patient in page_obj.object_list:
        patient.last_appointment = (
            patient.appointments.filter(date_time__lt=timezone.now())
            .order_by("-date_time")
            .first()
        )
        patient.next_appointment = (
            patient.appointments.filter(
                date_time__gte=timezone.now(),
            )
            .exclude(status=Appointment.STATUS_CANCELED)
            .order_by("date_time")
            .first()
        )
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "patients/list.html",
        {
            "patients": page_obj,
            "page_obj": page_obj,
            "search": search,
            "query_string": query_params.urlencode(),
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def patient_create_view(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Paciente cadastrado com sucesso.")
            return redirect("patients_list")
    else:
        form = PatientForm()

    return render(
        request,
        "patients/form.html",
        {
            "form": form,
            "title": "Novo paciente",
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def patient_detail_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    appointments = patient.appointments.order_by("-date_time")[:10]
    last_appointment = (
        patient.appointments.filter(date_time__lt=timezone.now())
        .order_by("-date_time")
        .first()
    )
    next_appointment = (
        patient.appointments.filter(date_time__gte=timezone.now())
        .exclude(status=Appointment.STATUS_CANCELED)
        .order_by("date_time")
        .first()
    )
    history_entries = patient.clinical_history_entries.order_by("-performed_at")[:5]

    return render(
        request,
        "patients/detail.html",
        {
            "patient": patient,
            "appointments": appointments,
            "last_appointment": last_appointment,
            "next_appointment": next_appointment,
            "history_entries": history_entries,
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def patient_edit_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Paciente atualizado com sucesso.")
            return redirect("patients_list")
    else:
        form = PatientForm(instance=patient)

    return render(
        request,
        "patients/form.html",
        {
            "form": form,
            "title": "Editar paciente",
            "patient": patient,
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def patient_delete_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        patient.delete()
        messages.info(request, "Paciente removido com sucesso.")
        return redirect("patients_list")

    return render(request, "patients/confirm_delete.html", {"patient": patient})


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def appointment_list_view(request):
    period = request.GET.get("period", "week")
    if period not in {"day", "week", "month"}:
        period = "week"

    reference_date = _parse_reference_date(request.GET.get("date", ""))
    start_day, end_day, start_dt, end_dt = _get_period_range(reference_date, period)
    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    appointments = (
        Appointment.objects.select_related("patient")
        .filter(date_time__gte=start_dt, date_time__lt=end_dt)
        .order_by("date_time")
    )

    if status_filter not in {"", *dict(Appointment.STATUS_CHOICES).keys()}:
        status_filter = ""

    if status_filter:
        appointments = appointments.filter(status=status_filter)

    if search:
        search_digits = re.sub(r"\D", "", search)
        formatted_cpf = (
            f"{search_digits[:3]}.{search_digits[3:6]}.{search_digits[6:9]}-{search_digits[9:]}"
            if len(search_digits) == 11
            else search
        )
        appointments = appointments.filter(
            Q(patient__full_name__icontains=search)
            | Q(patient__cpf__icontains=search)
            | Q(patient__cpf__icontains=formatted_cpf)
            | Q(treatment__icontains=search)
            | Q(status__icontains=search)
            | Q(notes__icontains=search)
        )

    if period == "day":
        title_period = f"Dia {start_day.strftime('%d/%m/%Y')}"
    elif period == "month":
        title_period = reference_date.strftime("Mes %m/%Y")
    else:
        title_period = (
            f"Semana {start_day.strftime('%d/%m/%Y')} ate "
            f"{(end_day - timedelta(days=1)).strftime('%d/%m/%Y')}"
        )

    paginator = Paginator(appointments, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "appointments/list.html",
        {
            "appointments": page_obj,
            "page_obj": page_obj,
            "period": period,
            "date_filter": reference_date.strftime("%Y-%m-%d"),
            "search": search,
            "status_filter": status_filter,
            "status_choices": Appointment.STATUS_CHOICES,
            "title_period": title_period,
            "query_string": query_params.urlencode(),
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def agenda_view(request):
    now = timezone.localtime()
    period = request.GET.get("period", "week")
    if period not in {"day", "week", "month"}:
        period = "week"

    reference_date = _parse_reference_date(request.GET.get("date", ""))
    start_day, end_day, start_dt, end_dt = _get_period_range(reference_date, period)
    status_filter = request.GET.get("status", "").strip()

    appointments = list(
        Appointment.objects.select_related("patient")
        .filter(date_time__gte=start_dt, date_time__lt=end_dt)
        .order_by("date_time")
    )
    if status_filter not in {"", *dict(Appointment.STATUS_CHOICES).keys()}:
        status_filter = ""
    if status_filter:
        appointments = [
            appointment
            for appointment in appointments
            if appointment.status == status_filter
        ]

    agenda_days = _build_agenda_days(appointments, start_day, end_day, now)
    agenda_totals = {
        "total": len(appointments),
        "scheduled": sum(1 for item in appointments if item.status == Appointment.STATUS_SCHEDULED),
        "completed": sum(1 for item in appointments if item.status == Appointment.STATUS_COMPLETED),
        "canceled": sum(1 for item in appointments if item.status == Appointment.STATUS_CANCELED),
        "late": sum(
            1
            for item in appointments
            if item.status == Appointment.STATUS_SCHEDULED and item.end_time < now
        ),
    }

    month_start = reference_date.replace(day=1)
    month_days = calendar.monthrange(reference_date.year, reference_date.month)[1]
    if reference_date.month == 12:
        month_end = reference_date.replace(year=reference_date.year + 1, month=1, day=1)
    else:
        month_end = reference_date.replace(month=reference_date.month + 1, day=1)

    month_appointments = Appointment.objects.filter(
        date_time__gte=timezone.make_aware(datetime.combine(month_start, datetime.min.time())),
        date_time__lt=timezone.make_aware(datetime.combine(month_end, datetime.min.time())),
    )
    day_counts = Counter(timezone.localtime(item.date_time).date() for item in month_appointments)

    first_weekday = month_start.weekday()
    calendar_cells = []
    for _ in range(first_weekday):
        calendar_cells.append({"is_empty": True})

    today = timezone.localdate()
    for day in range(1, month_days + 1):
        day_date = reference_date.replace(day=day)
        calendar_cells.append(
            {
                "is_empty": False,
                "date": day_date,
                "is_today": day_date == today,
                "is_selected": day_date == reference_date,
                "count": day_counts.get(day_date, 0),
            }
        )

    while len(calendar_cells) % 7 != 0:
        calendar_cells.append({"is_empty": True})

    if period == "day":
        title_period = f"Dia {start_day.strftime('%d/%m/%Y')}"
        previous_date = reference_date - timedelta(days=1)
        next_date = reference_date + timedelta(days=1)
    elif period == "month":
        title_period = reference_date.strftime("Mes %m/%Y")
        previous_date = (reference_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        next_date = (reference_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        title_period = (
            f"Semana {start_day.strftime('%d/%m/%Y')} ate "
            f"{(end_day - timedelta(days=1)).strftime('%d/%m/%Y')}"
        )
        previous_date = reference_date - timedelta(days=7)
        next_date = reference_date + timedelta(days=7)

    return render(
        request,
        "appointments/agenda.html",
        {
            "appointments": appointments,
            "agenda_days": agenda_days,
            "agenda_totals": agenda_totals,
            "period": period,
            "date_filter": reference_date.strftime("%Y-%m-%d"),
            "title_period": title_period,
            "calendar_cells": calendar_cells,
            "calendar_month_label": reference_date.strftime("%B de %Y"),
            "previous_date": previous_date.strftime("%Y-%m-%d"),
            "next_date": next_date.strftime("%Y-%m-%d"),
            "status_filter": status_filter,
            "status_choices": Appointment.STATUS_CHOICES,
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def appointment_create_view(request):
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            appointment.updated_by = request.user
            appointment.save()
            _ensure_history_for_completed_appointment(appointment, request.user)
            messages.success(request, "Consulta cadastrada com sucesso.")
            return redirect("appointments_list")
    else:
        form = AppointmentForm()

    return render(
        request,
        "appointments/form.html",
        {
            "form": form,
            "title": "Nova consulta",
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def appointment_edit_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == "POST":
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            is_reschedule = bool({"date_time", "duration_minutes"} & set(form.changed_data))
            appointment = form.save(commit=False)
            appointment.updated_by = request.user
            appointment.save()
            _ensure_history_for_completed_appointment(appointment, request.user)
            if is_reschedule:
                messages.success(request, "Consulta reagendada com sucesso.")
            else:
                messages.success(request, "Consulta atualizada com sucesso.")
            return redirect("appointments_list")
    else:
        initial = {
            "date_time": timezone.localtime(appointment.date_time).strftime(
                "%Y-%m-%dT%H:%M"
            )
        }
        form = AppointmentForm(instance=appointment, initial=initial)

    return render(
        request,
        "appointments/form.html",
        {
            "form": form,
            "title": "Editar consulta",
            "appointment": appointment,
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def appointment_delete_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == "POST":
        appointment.delete()
        messages.info(request, "Consulta removida com sucesso.")
        return redirect("appointments_list")

    return render(
        request,
        "appointments/confirm_delete.html",
        {"appointment": appointment},
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST, ROLE_RECEPTION)
def appointment_cancel_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == "POST":
        appointment.status = Appointment.STATUS_CANCELED
        appointment.updated_by = request.user
        appointment.save(update_fields=["status", "updated_by"])
        messages.info(request, "Consulta cancelada com sucesso.")
        return redirect("appointments_list")

    return render(
        request,
        "appointments/confirm_cancel.html",
        {"appointment": appointment},
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def dental_record_detail_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    record, _ = DentalRecord.objects.get_or_create(patient=patient)
    edit_odontogram_id = request.GET.get("edit_odontogram")
    edit_history_id = request.GET.get("edit_history")

    record_form = DentalRecordForm(instance=record)
    odontogram_instance = (
        get_object_or_404(
            OdontogramEntry,
            id=edit_odontogram_id,
            record=record,
        )
        if edit_odontogram_id
        else None
    )
    history_instance = (
        get_object_or_404(
            ClinicalHistoryEntry,
            id=edit_history_id,
            patient=patient,
        )
        if edit_history_id
        else None
    )
    odontogram_form = OdontogramEntryForm(instance=odontogram_instance)
    history_form = ClinicalHistoryEntryForm(instance=history_instance)
    history_form.fields["appointment"].queryset = Appointment.objects.filter(patient=patient)
    attachment_form = PatientAttachmentForm()

    odontogram_entries = record.odontogram_entries.order_by("tooth_code")
    entry_map = {entry.tooth_code: entry for entry in odontogram_entries}
    tooth_rows = []
    for row in ODONTOGRAM_ROWS:
        tooth_rows.append([{"code": code, "entry": entry_map.get(code)} for code in row])

    history_entries = ClinicalHistoryEntry.objects.filter(patient=patient)
    attachments = patient.attachments.all()
    appointments = patient.appointments.order_by("-date_time")[:20]

    return render(
        request,
        "records/detail.html",
        {
            "patient": patient,
            "record": record,
            "record_form": record_form,
            "odontogram_form": odontogram_form,
            "history_form": history_form,
            "attachment_form": attachment_form,
            "odontogram_entries": odontogram_entries,
            "tooth_rows": tooth_rows,
            "history_entries": history_entries,
            "attachments": attachments,
            "appointments": appointments,
            "odontogram_instance": odontogram_instance,
            "history_instance": history_instance,
        },
    )


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def dental_record_update_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    record, _ = DentalRecord.objects.get_or_create(patient=patient)

    if request.method == "POST":
        form = DentalRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Prontuario atualizado com sucesso.")
        else:
            messages.error(request, "Nao foi possivel atualizar o prontuario.")

    return redirect("patient_record", patient_id=patient.id)


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def odontogram_entry_upsert_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    record, _ = DentalRecord.objects.get_or_create(patient=patient)

    if request.method == "POST":
        form = OdontogramEntryForm(request.POST)
        if form.is_valid():
            tooth_code = form.cleaned_data["tooth_code"]
            condition = form.cleaned_data["condition"]
            notes = form.cleaned_data["notes"]
            OdontogramEntry.objects.update_or_create(
                record=record,
                tooth_code=tooth_code,
                defaults={
                    "condition": condition,
                    "notes": notes,
                },
            )
            messages.success(request, "Odontograma atualizado.")
        else:
            messages.error(request, "Nao foi possivel salvar a entrada de odontograma.")

    return redirect("patient_record", patient_id=patient.id)


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def odontogram_entry_delete_view(request, patient_id, entry_id):
    patient = get_object_or_404(Patient, id=patient_id)
    entry = get_object_or_404(
        OdontogramEntry,
        id=entry_id,
        record__patient=patient,
    )

    if request.method == "POST":
        entry.delete()
        messages.info(request, "Entrada de odontograma removida.")

    return redirect("patient_record", patient_id=patient.id)


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def clinical_history_create_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        form = ClinicalHistoryEntryForm(request.POST)
        form.fields["appointment"].queryset = Appointment.objects.filter(patient=patient)
        if form.is_valid():
            history_item = form.save(commit=False)
            history_item.patient = patient
            history_item.created_by = request.user
            history_item.updated_by = request.user
            history_item.save()
            messages.success(request, "Historico clinico registrado.")
        else:
            messages.error(request, "Nao foi possivel registrar o historico clinico.")

    return redirect("patient_record", patient_id=patient.id)


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def clinical_history_update_view(request, patient_id, entry_id):
    patient = get_object_or_404(Patient, id=patient_id)
    entry = get_object_or_404(
        ClinicalHistoryEntry,
        id=entry_id,
        patient=patient,
    )

    if request.method == "POST":
        form = ClinicalHistoryEntryForm(request.POST, instance=entry)
        form.fields["appointment"].queryset = Appointment.objects.filter(patient=patient)
        if form.is_valid():
            history_item = form.save(commit=False)
            history_item.patient = patient
            history_item.updated_by = request.user
            history_item.save()
            messages.success(request, "Historico clinico atualizado.")
        else:
            messages.error(request, "Nao foi possivel atualizar o historico clinico.")

    return redirect("patient_record", patient_id=patient.id)


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def clinical_history_delete_view(request, patient_id, entry_id):
    patient = get_object_or_404(Patient, id=patient_id)
    entry = get_object_or_404(
        ClinicalHistoryEntry,
        id=entry_id,
        patient=patient,
    )

    if request.method == "POST":
        entry.delete()
        messages.info(request, "Historico clinico removido.")

    return redirect("patient_record", patient_id=patient.id)


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def patient_attachment_create_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        form = PatientAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.patient = patient
            attachment.uploaded_by = request.user
            attachment.save()
            messages.success(request, "Anexo adicionado.")
        else:
            messages.error(request, "Nao foi possivel adicionar o anexo.")

    return redirect("patient_record", patient_id=patient.id)


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def patient_attachment_delete_view(request, patient_id, attachment_id):
    patient = get_object_or_404(Patient, id=patient_id)
    attachment = get_object_or_404(
        PatientAttachment,
        id=attachment_id,
        patient=patient,
    )

    if request.method == "POST":
        attachment.file.delete(save=False)
        attachment.delete()
        messages.info(request, "Anexo removido.")

    return redirect("patient_record", patient_id=patient.id)


@role_required(ROLE_ADMIN, ROLE_DENTIST)
def dental_record_pdf_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    record, _ = DentalRecord.objects.get_or_create(patient=patient)
    odontogram_entries = record.odontogram_entries.order_by("tooth_code")
    history_entries = ClinicalHistoryEntry.objects.filter(patient=patient).order_by("-performed_at")[:20]
    attachments = patient.attachments.all()[:20]

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="prontuario_{patient.id}.pdf"'
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "RecordTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=16,
        spaceAfter=14,
    )
    section_style = ParagraphStyle(
        "RecordSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "RecordBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=5,
    )

    def paragraph(label, value):
        return Paragraph(f"<b>{escape(label)}:</b> {escape(str(value or '-'))}", body_style)

    story = [
        Paragraph("DentalCore - Prontuario Odontologico", title_style),
        paragraph("Emitido em", timezone.localtime().strftime("%d/%m/%Y %H:%M")),
        paragraph("Paciente", patient.full_name),
        paragraph("CPF", patient.cpf),
        paragraph("Telefone", patient.phone),
        paragraph(
            "Data de nascimento",
            patient.birth_date.strftime("%d/%m/%Y") if patient.birth_date else "-",
        ),
        Spacer(1, 0.2 * cm),
        Paragraph("Anamnese", section_style),
        paragraph("Queixa principal", record.chief_complaint),
        paragraph("Historico medico", record.medical_history),
        paragraph("Doencas sistemicas", record.systemic_diseases),
        paragraph("Alergias", record.allergies),
        paragraph("Medicacoes", record.medications),
        paragraph("Cirurgias e internacoes", record.surgeries),
        paragraph("Alteracoes de sangramento", record.bleeding_disorders),
        paragraph("Gestante", record.pregnancy),
        paragraph("Pressao arterial", record.blood_pressure),
        paragraph("Historico odontologico", record.dental_history),
        paragraph("Habitos", record.habits),
        paragraph("Plano de tratamento", record.treatment_plan),
        Paragraph("Odontograma", section_style),
    ]

    if odontogram_entries:
        odontogram_data = [["Dente", "Condicao", "Observacoes"]]
        odontogram_data.extend(
            [
                Paragraph(escape(entry.tooth_code), body_style),
                Paragraph(escape(entry.condition), body_style),
                Paragraph(escape(entry.notes or "-"), body_style),
            ]
            for entry in odontogram_entries
        )
        odontogram_table = Table(odontogram_data, colWidths=[2 * cm, 5 * cm, 9 * cm])
        odontogram_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f1ef")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfc8bb")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(odontogram_table)
    else:
        story.append(Paragraph("Sem entradas no odontograma.", body_style))

    story.append(Paragraph("Historico clinico (ultimos 20)", section_style))
    if history_entries:
        for item in history_entries:
            story.append(
                paragraph(
                    timezone.localtime(item.performed_at).strftime("%d/%m/%Y %H:%M"),
                    item.procedure_name,
                )
            )
            story.append(paragraph("Profissional", item.professional))
            story.append(paragraph("Descricao", item.description))
            story.append(Spacer(1, 0.1 * cm))
    else:
        story.append(Paragraph("Sem historico clinico.", body_style))

    story.append(Paragraph("Documentos anexados", section_style))
    if attachments:
        for attachment in attachments:
            story.append(
                paragraph(
                    attachment.title,
                    f"Arquivo: {attachment.file.name} | Enviado em: {timezone.localtime(attachment.uploaded_at):%d/%m/%Y %H:%M}",
                )
            )
            if attachment.description:
                story.append(paragraph("Descricao", attachment.description))
    else:
        story.append(Paragraph("Sem documentos anexados.", body_style))

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Prontuario-{patient.full_name}",
    )
    document.build(story)
    return response
