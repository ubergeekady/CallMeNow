# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-10 17:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0024_auto_20171110_1701'),
    ]

    operations = [
        migrations.AddField(
            model_name='callqueue',
            name='ipaddress',
            field=models.CharField(default='1.1.1.1', max_length=100),
            preserve_default=False,
        ),
    ]
