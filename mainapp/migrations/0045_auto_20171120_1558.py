# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-20 15:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0044_notes_timestamp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='widgetagent',
            name='userId',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mainapp.UserProfile'),
        ),
        migrations.AlterField(
            model_name='widgetagent',
            name='widgetId',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mainapp.Widget'),
        ),
    ]