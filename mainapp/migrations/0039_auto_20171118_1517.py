# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-18 15:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0038_leads_lead_owner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leads',
            name='lead_owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='mainapp.UserProfile'),
        ),
    ]