# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-21 19:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0051_auto_20171120_1845'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calls',
            name='widget',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mainapp.Widget'),
        ),
    ]