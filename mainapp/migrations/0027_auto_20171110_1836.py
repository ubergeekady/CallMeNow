# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-10 18:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0026_calls'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calls',
            name='plivo_aleg_duration',
            field=models.IntegerField(blank=True, default=0),
        ),
    ]
