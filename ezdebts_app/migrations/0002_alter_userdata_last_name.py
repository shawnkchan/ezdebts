# Generated by Django 4.1.4 on 2024-06-13 09:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ezdebts_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userdata",
            name="last_name",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
