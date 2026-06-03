from datetime import timedelta
import shutil
import tempfile

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import AppointmentForm
from .models import (
    Appointment,
    ClinicalHistoryEntry,
    DentalRecord,
    OdontogramEntry,
    Patient,
    PatientAttachment,
)
from .views import (
    dashboard_view,
    dental_record_detail_view,
    patient_list_view,
    patient_detail_view,
    register_view,
)


@override_settings(SECURE_SSL_REDIRECT=False)
class AuthAccessTestCase(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_public_registration_is_disabled_by_default(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("login"))

    @override_settings(ALLOW_PUBLIC_REGISTRATION=True)
    def test_public_registration_can_be_enabled(self):
        request = RequestFactory().get(reverse("register"))
        request.user = AnonymousUser()
        response = register_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Criar conta", response.content)


@override_settings(SECURE_SSL_REDIRECT=False)
class BaseAuthTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="TestPass123!")
        self.user.groups.add(Group.objects.get(name="Administrador"))
        self.client = Client(HTTP_HOST="localhost")
        logged_in = self.client.login(username="tester", password="TestPass123!")
        self.assertTrue(logged_in)


class AppointmentConflictTestCase(BaseAuthTestCase):
    def test_blocks_conflict_for_same_datetime(self):
        patient_a = Patient.objects.create(
            full_name="Paciente A",
            cpf="111.111.111-11",
            phone="11911111111",
        )
        patient_b = Patient.objects.create(
            full_name="Paciente B",
            cpf="222.222.222-22",
            phone="11922222222",
        )

        slot = timezone.localtime().replace(second=0, microsecond=0) + timedelta(days=1)

        Appointment.objects.create(
            patient=patient_a,
            date_time=slot,
            treatment="Limpeza",
            status=Appointment.STATUS_SCHEDULED,
        )

        form = AppointmentForm(
            data={
                "patient": patient_b.id,
                "date_time": slot.strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 60,
                "treatment": "Consulta",
                "status": Appointment.STATUS_SCHEDULED,
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("date_time", form.errors)

    def test_blocks_overlap_within_duration(self):
        patient_a = Patient.objects.create(
            full_name="Paciente A2",
            cpf="666.666.666-66",
            phone="11966666666",
        )
        patient_b = Patient.objects.create(
            full_name="Paciente B2",
            cpf="777.777.777-77",
            phone="11977777777",
        )

        slot = timezone.localtime().replace(second=0, microsecond=0) + timedelta(days=2)

        Appointment.objects.create(
            patient=patient_a,
            date_time=slot,
            treatment="Limpeza",
            status=Appointment.STATUS_SCHEDULED,
        )

        # Attempt to schedule within default duration (30-60 minutes) afterwards
        nearby = slot + timedelta(minutes=30)
        form = AppointmentForm(
            data={
                "patient": patient_b.id,
                "date_time": nearby.strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 60,
                "treatment": "Consulta",
                "status": Appointment.STATUS_SCHEDULED,
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("date_time", form.errors)

    def test_allows_back_to_back_appointment_after_duration(self):
        patient_a = Patient.objects.create(
            full_name="Paciente A3",
            cpf="888.888.888-88",
            phone="11988888888",
        )
        patient_b = Patient.objects.create(
            full_name="Paciente B3",
            cpf="999.999.999-99",
            phone="11999999999",
        )

        slot = timezone.localtime().replace(second=0, microsecond=0) + timedelta(days=3)

        Appointment.objects.create(
            patient=patient_a,
            date_time=slot,
            treatment="Limpeza",
            status=Appointment.STATUS_SCHEDULED,
        )

        next_slot = slot + timedelta(minutes=60)
        form = AppointmentForm(
            data={
                "patient": patient_b.id,
                "date_time": next_slot.strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 60,
                "treatment": "Consulta",
                "status": Appointment.STATUS_SCHEDULED,
                "notes": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_canceled_appointment_does_not_block_slot(self):
        patient_a = Patient.objects.create(
            full_name="Paciente Cancelado",
            cpf="123.123.123-12",
            phone="11912312312",
        )
        patient_b = Patient.objects.create(
            full_name="Paciente Livre",
            cpf="321.321.321-32",
            phone="11932132132",
        )

        slot = timezone.localtime().replace(second=0, microsecond=0) + timedelta(days=4)

        Appointment.objects.create(
            patient=patient_a,
            date_time=slot,
            treatment="Limpeza",
            status=Appointment.STATUS_CANCELED,
        )

        form = AppointmentForm(
            data={
                "patient": patient_b.id,
                "date_time": slot.strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 60,
                "treatment": "Consulta",
                "status": Appointment.STATUS_SCHEDULED,
                "notes": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_same_appointment_does_not_conflict_with_itself(self):
        patient = Patient.objects.create(
            full_name="Paciente Edicao",
            cpf="456.456.456-45",
            phone="11945645645",
        )

        slot = timezone.localtime().replace(second=0, microsecond=0) + timedelta(days=5)
        appointment = Appointment.objects.create(
            patient=patient,
            date_time=slot,
            treatment="Limpeza",
            status=Appointment.STATUS_SCHEDULED,
        )

        form = AppointmentForm(
            instance=appointment,
            data={
                "patient": patient.id,
                "date_time": slot.strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 60,
                "treatment": "Limpeza atualizada",
                "status": Appointment.STATUS_SCHEDULED,
                "notes": "",
            },
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_blocks_overlap_using_existing_custom_duration(self):
        patient_a = Patient.objects.create(
            full_name="Paciente Longo",
            cpf="654.654.654-65",
            phone="11965465465",
        )
        patient_b = Patient.objects.create(
            full_name="Paciente Sobreposto",
            cpf="987.987.987-98",
            phone="11998798798",
        )

        slot = timezone.localtime().replace(second=0, microsecond=0) + timedelta(days=7)
        Appointment.objects.create(
            patient=patient_a,
            date_time=slot,
            duration_minutes=120,
            treatment="Cirurgia",
            status=Appointment.STATUS_SCHEDULED,
        )

        form = AppointmentForm(
            data={
                "patient": patient_b.id,
                "date_time": (slot + timedelta(minutes=90)).strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 30,
                "treatment": "Retorno",
                "status": Appointment.STATUS_SCHEDULED,
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("date_time", form.errors)


class PatientCrudTestCase(BaseAuthTestCase):
    def test_create_patient_view(self):
        response = self.client.post(
            reverse("patients_create"),
            data={
                "full_name": "Paciente Novo",
                "cpf": "111.222.333-44",
                "phone": "11911112222",
                "birth_date": "1990-05-10",
                "notes": "Primeira consulta",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("patients_list"))
        self.assertTrue(Patient.objects.filter(cpf="111.222.333-44").exists())

    def test_patient_search_by_cpf(self):
        Patient.objects.create(
            full_name="Paciente Busca",
            cpf="999.888.777-66",
            phone="11999998888",
        )

        request = RequestFactory().get(reverse("patients_list"), {"search": "999.888"})
        request.user = self.user
        response = patient_list_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Paciente Busca", response.content)

    def test_patient_list_is_paginated(self):
        patients = [
            Patient(
                full_name=f"Paciente {index:02d}",
                cpf=f"000.000.000-{index:02d}",
                phone="11900000000",
            )
            for index in range(12)
        ]
        Patient.objects.bulk_create(patients)

        request = RequestFactory().get(reverse("patients_list"))
        request.user = self.user
        response = patient_list_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pagina 1 de 2", response.content)

    def test_patient_detail_shows_related_context(self):
        patient = Patient.objects.create(
            full_name="Paciente Detalhe",
            cpf="123.456.789-01",
            phone="11912345678",
        )
        Appointment.objects.create(
            patient=patient,
            date_time=timezone.localtime() + timedelta(days=1),
            duration_minutes=30,
            treatment="Retorno",
            status=Appointment.STATUS_SCHEDULED,
        )

        request = RequestFactory().get(reverse("patients_detail", args=[patient.id]))
        request.user = self.user
        response = patient_detail_view(request, patient.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Paciente Detalhe", response.content)
        self.assertIn(b"Retorno", response.content)


class AppointmentViewTestCase(BaseAuthTestCase):
    def test_create_appointment_view(self):
        patient = Patient.objects.create(
            full_name="Paciente Consulta",
            cpf="222.333.444-55",
            phone="11922223333",
        )
        slot = timezone.localtime().replace(second=0, microsecond=0) + timedelta(days=6)

        response = self.client.post(
            reverse("appointments_create"),
            data={
                "patient": patient.id,
                "date_time": slot.strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 45,
                "treatment": "Avaliacao",
                "status": Appointment.STATUS_SCHEDULED,
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("appointments_list"))
        self.assertTrue(
            Appointment.objects.filter(
                patient=patient,
                treatment="Avaliacao",
                duration_minutes=45,
            ).exists()
        )

    def test_appointment_list_search_and_pagination(self):
        patient = Patient.objects.create(
            full_name="Paciente Agenda",
            cpf="111.333.555-77",
            phone="11911113333",
        )
        start = timezone.localtime().replace(second=0, microsecond=0) + timedelta(days=8)
        appointments = [
            Appointment(
                patient=patient,
                date_time=start + timedelta(hours=index),
                duration_minutes=30,
                treatment="Profilaxia" if index == 0 else f"Consulta {index:02d}",
                status=Appointment.STATUS_SCHEDULED,
            )
            for index in range(12)
        ]
        Appointment.objects.bulk_create(appointments)

        response = self.client.get(
            reverse("appointments_list"),
            {
                "period": "month",
                "date": start.strftime("%Y-%m-%d"),
                "search": "Consulta",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pagina 1 de 2")
        self.assertContains(response, "30 min")
        self.assertNotContains(response, "Profilaxia")

    def test_cancel_appointment_view_keeps_appointment_with_canceled_status(self):
        patient = Patient.objects.create(
            full_name="Paciente Cancelar",
            cpf="222.444.666-88",
            phone="11922224444",
        )
        appointment = Appointment.objects.create(
            patient=patient,
            date_time=timezone.localtime() + timedelta(days=9),
            treatment="Consulta",
            status=Appointment.STATUS_SCHEDULED,
        )

        response = self.client.post(reverse("appointments_cancel", args=[appointment.id]))
        appointment.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(appointment.status, Appointment.STATUS_CANCELED)
        self.assertEqual(appointment.updated_by, self.user)

    def test_cannot_create_appointment_in_past(self):
        patient = Patient.objects.create(
            full_name="Paciente Passado",
            cpf="333.555.777-99",
            phone="11933335555",
        )
        form = AppointmentForm(
            data={
                "patient": patient.id,
                "date_time": (timezone.localtime() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 60,
                "treatment": "Consulta",
                "status": Appointment.STATUS_SCHEDULED,
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("date_time", form.errors)

    def test_cannot_complete_future_appointment(self):
        patient = Patient.objects.create(
            full_name="Paciente Futuro",
            cpf="444.666.888-00",
            phone="11944446666",
        )
        form = AppointmentForm(
            data={
                "patient": patient.id,
                "date_time": (timezone.localtime() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 60,
                "treatment": "Consulta",
                "status": Appointment.STATUS_COMPLETED,
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)


class DashboardMetricsTestCase(BaseAuthTestCase):
    def test_dashboard_month_metrics_present(self):
        patient = Patient.objects.create(
            full_name="Paciente M",
            cpf="333.333.333-33",
            phone="11933333333",
        )
        now = timezone.localtime()

        Appointment.objects.create(
            patient=patient,
            date_time=now + timedelta(days=1),
            treatment="Limpeza",
            status=Appointment.STATUS_SCHEDULED,
        )
        Appointment.objects.create(
            patient=patient,
            date_time=now + timedelta(days=2),
            treatment="Limpeza",
            status=Appointment.STATUS_COMPLETED,
        )
        Appointment.objects.create(
            patient=patient,
            date_time=now + timedelta(days=3),
            treatment="Canal",
            status=Appointment.STATUS_CANCELED,
        )

        request = RequestFactory().get(reverse("dashboard"))
        request.user = self.user
        response = dashboard_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Consultas no periodo", response.content)
        self.assertIn(b"Canceladas no periodo", response.content)
        self.assertIn(b"Pacientes recorrentes", response.content)
        self.assertIn(b"Minutos ocupados", response.content)
        self.assertIn(b"bar-fill", response.content)

    def test_dashboard_period_selector_uses_current_day_month_and_year(self):
        patient = Patient.objects.create(
            full_name="Paciente Periodo",
            cpf="555.555.555-55",
            phone="11955555555",
        )
        now = timezone.localtime().replace(second=0, microsecond=0)

        Appointment.objects.create(
            patient=patient,
            date_time=now,
            treatment="TratamentoDia",
            status=Appointment.STATUS_SCHEDULED,
        )
        Appointment.objects.create(
            patient=patient,
            date_time=now + timedelta(days=2),
            treatment="TratamentoMes",
            status=Appointment.STATUS_COMPLETED,
        )
        other_month = 12 if now.month != 12 else 11
        Appointment.objects.create(
            patient=patient,
            date_time=now.replace(month=other_month, day=10, hour=10, minute=0),
            treatment="TratamentoAno",
            status=Appointment.STATUS_COMPLETED,
        )

        for period, label, expected, unexpected in [
            ("day", b"Dia atual", b"TratamentoDia", b"TratamentoMes"),
            ("month", b"Mes atual", b"TratamentoMes", b"TratamentoAno"),
            ("year", b"Ano atual", b"TratamentoAno", b"TratamentoFora"),
        ]:
            request = RequestFactory().get(f"{reverse('dashboard')}?period={period}")
            request.user = self.user
            response = dashboard_view(request)

            self.assertEqual(response.status_code, 200)
            self.assertIn(label, response.content)
            self.assertIn(b"Periodo selecionado", response.content)
            self.assertIn(expected, response.content)
            self.assertNotIn(unexpected, response.content)


class DentalRecordViewsTestCase(BaseAuthTestCase):
    def test_record_detail_creates_record(self):
        patient = Patient.objects.create(
            full_name="Paciente Prontuario",
            cpf="777.888.999-00",
            phone="11977778888",
        )

        request = RequestFactory().get(reverse("patient_record", args=[patient.id]))
        request.user = self.user
        response = dental_record_detail_view(request, patient.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(DentalRecord.objects.filter(patient=patient).exists())
        self.assertIn(b"Anamnese", response.content)
        self.assertIn(b"Odontograma", response.content)
        self.assertIn(b"Evolucao", response.content)
        self.assertIn(b"Consultas", response.content)
        self.assertIn(b"Documentos", response.content)

    def test_update_record_odontogram_and_history(self):
        patient = Patient.objects.create(
            full_name="Paciente Clinico",
            cpf="333.444.555-66",
            phone="11933334444",
        )

        response = self.client.post(
            reverse("patient_record_update", args=[patient.id]),
            data={
                "chief_complaint": "Dor ao mastigar",
                "medical_history": "Historico longo",
                "systemic_diseases": "Hipertensao controlada",
                "allergies": "Nenhuma",
                "medications": "Losartana",
                "surgeries": "Nenhuma",
                "bleeding_disorders": "Nao relatado",
                "pregnancy": "Nao se aplica",
                "blood_pressure": "120/80",
                "dental_history": "Tratamento ortodontico previo",
                "habits": "Bruxismo",
                "treatment_plan": "Acompanhamento",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("patient_record", args=[patient.id]))
        patient.dental_record.refresh_from_db()
        self.assertEqual(patient.dental_record.chief_complaint, "Dor ao mastigar")
        self.assertEqual(patient.dental_record.systemic_diseases, "Hipertensao controlada")
        self.assertEqual(patient.dental_record.blood_pressure, "120/80")
        self.assertEqual(patient.dental_record.dental_history, "Tratamento ortodontico previo")

        response = self.client.post(
            reverse("patient_record_odontogram", args=[patient.id]),
            data={
                "tooth_code": "16",
                "condition": "Caries",
                "notes": "Restaurar",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("patient_record", args=[patient.id]))
        self.assertTrue(
            OdontogramEntry.objects.filter(
                record=patient.dental_record,
                tooth_code="16",
                condition="Caries",
            ).exists()
        )
        odontogram_entry = OdontogramEntry.objects.get(
            record=patient.dental_record,
            tooth_code="16",
        )
        request = RequestFactory().get(
            reverse("patient_record", args=[patient.id]),
            {"edit_odontogram": odontogram_entry.id},
        )
        request.user = self.user
        response = dental_record_detail_view(request, patient.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Editar dente 16", response.content)

        performed_at = timezone.localtime().replace(second=0, microsecond=0)
        response = self.client.post(
            reverse("patient_record_history", args=[patient.id]),
            data={
                "appointment": "",
                "procedure_name": "Avaliacao inicial",
                "description": "Paciente avaliado",
                "professional": "Dra. Teste",
                "performed_at": performed_at.strftime("%Y-%m-%dT%H:%M"),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("patient_record", args=[patient.id]))
        self.assertTrue(
            ClinicalHistoryEntry.objects.filter(
                patient=patient,
                procedure_name="Avaliacao inicial",
            ).exists()
        )
        history_entry = ClinicalHistoryEntry.objects.get(
            patient=patient,
            procedure_name="Avaliacao inicial",
        )

        response = self.client.post(
            reverse("patient_record_history_update", args=[patient.id, history_entry.id]),
            data={
                "appointment": "",
                "procedure_name": "Avaliacao revisada",
                "description": "Paciente reavaliado",
                "professional": "Dra. Revisada",
                "performed_at": performed_at.strftime("%Y-%m-%dT%H:%M"),
            },
        )
        history_entry.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("patient_record", args=[patient.id]))
        self.assertEqual(history_entry.procedure_name, "Avaliacao revisada")
        self.assertEqual(history_entry.description, "Paciente reavaliado")
        self.assertEqual(history_entry.updated_by, self.user)

    def test_upload_and_delete_patient_attachment(self):
        patient = Patient.objects.create(
            full_name="Paciente Documento",
            cpf="555.666.777-88",
            phone="11955556666",
        )
        temp_dir = tempfile.mkdtemp()

        try:
            with override_settings(MEDIA_ROOT=temp_dir):
                response = self.client.post(
                    reverse("patient_record_attachment_create", args=[patient.id]),
                    data={
                        "title": "Radiografia panoramica",
                        "file": SimpleUploadedFile(
                            "radiografia.txt",
                            b"conteudo do exame",
                            content_type="text/plain",
                        ),
                        "description": "Exame inicial",
                    },
                )

                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], reverse("patient_record", args=[patient.id]))
                attachment = PatientAttachment.objects.get(patient=patient)
                self.assertEqual(attachment.title, "Radiografia panoramica")
                self.assertEqual(attachment.uploaded_by, self.user)
                self.assertTrue(attachment.file.name.startswith("patient_attachments/"))

                response = self.client.post(
                    reverse(
                        "patient_record_attachment_delete",
                        args=[patient.id, attachment.id],
                    )
                )

                self.assertEqual(response.status_code, 302)
                self.assertFalse(PatientAttachment.objects.filter(id=attachment.id).exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class DentalRecordPdfTestCase(BaseAuthTestCase):
    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_export_record_pdf(self):
        patient = Patient.objects.create(
            full_name="Paciente PDF",
            cpf="444.444.444-44",
            phone="11944444444",
        )
        record = DentalRecord.objects.create(patient=patient, chief_complaint="Dor")
        OdontogramEntry.objects.create(
            record=record,
            tooth_code="16",
            condition="Caries",
            notes="Teste",
        )
        ClinicalHistoryEntry.objects.create(
            patient=patient,
            procedure_name="Avaliacao",
            description="Teste clinico",
            professional="Dr. Teste",
        )

        response = self.client.get(reverse("patient_record_pdf", args=[patient.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertGreater(len(response.content), 100)
