from django.db import migrations


def create_default_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ["Administrador", "Dentista", "Recepcao"]:
        Group.objects.get_or_create(name=name)


def remove_default_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Administrador", "Dentista", "Recepcao"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0005_appointment_created_by_appointment_updated_by_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_default_groups, remove_default_groups),
    ]
