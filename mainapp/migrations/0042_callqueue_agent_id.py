# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-18 21:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0041_calls_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='callqueue',
            name='agent_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
