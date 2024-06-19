# Generated by Django 4.1.4 on 2024-06-16 04:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ezdebts_app", "0003_testmodel"),
    ]

    operations = [
        migrations.CreateModel(
            name="Currencies",
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
                ("code", models.CharField(max_length=3, unique=True)),
                ("name", models.CharField(max_length=50, unique=True)),
                ("symbol", models.CharField(max_length=5, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Expenses",
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
                ("quantity", models.DecimalField(decimal_places=2, max_digits=100)),
                (
                    "currency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expenses",
                        to="ezdebts_app.currencies",
                    ),
                ),
                (
                    "debtor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="debts",
                        to="ezdebts_app.userdata",
                    ),
                ),
                (
                    "lender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="receivables",
                        to="ezdebts_app.userdata",
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(name="TestModel",),
    ]