# Generated by Django 3.0.5 on 2021-02-22 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(model_name="tenantdata", name="active", field=models.BooleanField(default=True),),
    ]
