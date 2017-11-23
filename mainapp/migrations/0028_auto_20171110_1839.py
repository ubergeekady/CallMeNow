# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-10 18:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0027_auto_20171110_1836'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calls',
            name='plivo_aleg_bill',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AlterField(
            model_name='calls',
            name='plivo_bleg_bill',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AlterField(
            model_name='calls',
            name='total_bill',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=5),
        ),
    ]
