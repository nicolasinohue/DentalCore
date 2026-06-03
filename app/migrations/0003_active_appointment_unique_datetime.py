from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0002_dental_record_and_history"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.UniqueConstraint(
                condition=~models.Q(status="cancelado"),
                fields=("date_time",),
                name="unique_active_appointment_datetime",
            ),
        ),
    ]
