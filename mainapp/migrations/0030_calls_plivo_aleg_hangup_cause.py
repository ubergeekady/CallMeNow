# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-11 11:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0029_remove_calls_plivo_bleg_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='calls',
            name='plivo_aleg_hangup_cause',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]