# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-11 13:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0030_calls_plivo_aleg_hangup_cause'),
    ]

    operations = [
        migrations.AddField(
            model_name='calls',
            name='plivo_bleg_hangup_cause',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name='calls',
            name='plivo_aleg_bill',
            field=models.DecimalField(blank=True, decimal_places=4, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='calls',
            name='plivo_bleg_bill',
            field=models.DecimalField(blank=True, decimal_places=4, default=0, max_digits=10),
        ),
    ]