# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-12-04 10:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0070_accounts_firstpromoter_authid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accounts',
            name='callerId',
            field=models.CharField(blank=True, default='', max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='email_completed_calls',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='email_missed_calls',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='email_new_lead',
            field=models.BooleanField(default=True),
        ),
    ]