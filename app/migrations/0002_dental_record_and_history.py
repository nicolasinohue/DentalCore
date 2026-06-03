from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClinicalHistoryEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("procedure_name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("professional", models.CharField(blank=True, max_length=120)),
                ("performed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "appointment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="history_entries",
                        to="app.appointment",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="clinical_history_entries",
                        to="app.patient",
                    ),
                ),
            ],
            options={
                "verbose_name": "Historico clinico",
                "verbose_name_plural": "Historicos clinicos",
                "ordering": ["-performed_at"],
            },
        ),
        migrations.CreateModel(
            name="DentalRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("chief_complaint", models.TextField(blank=True)),
                ("medical_history", models.TextField(blank=True)),
                ("allergies", models.TextField(blank=True)),
                ("medications", models.TextField(blank=True)),
                ("habits", models.TextField(blank=True)),
                ("treatment_plan", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "patient",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dental_record",
                        to="app.patient",
                    ),
                ),
            ],
            options={
                "verbose_name": "Prontuario odontologico",
                "verbose_name_plural": "Prontuarios odontologicos",
            },
        ),
        migrations.CreateModel(
            name="OdontogramEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tooth_code",
                    models.CharField(
                        choices=[
                            ("18", "18"), ("17", "17"), ("16", "16"), ("15", "15"),
                            ("14", "14"), ("13", "13"), ("12", "12"), ("11", "11"),
                            ("21", "21"), ("22", "22"), ("23", "23"), ("24", "24"),
                            ("25", "25"), ("26", "26"), ("27", "27"), ("28", "28"),
                            ("48", "48"), ("47", "47"), ("46", "46"), ("45", "45"),
                            ("44", "44"), ("43", "43"), ("42", "42"), ("41", "41"),
                            ("31", "31"), ("32", "32"), ("33", "33"), ("34", "34"),
                            ("35", "35"), ("36", "36"), ("37", "37"), ("38", "38"),
                        ],
                        max_length=3,
                    ),
                ),
                ("condition", models.CharField(max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="odontogram_entries",
                        to="app.dentalrecord",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entrada de odontograma",
                "verbose_name_plural": "Entradas de odontograma",
                "ordering": ["tooth_code"],
                "unique_together": {("record", "tooth_code")},
            },
        ),
    ]
