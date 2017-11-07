# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-02 16:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0007_auto_20171102_1523'),
    ]

    operations = [
        migrations.CreateModel(
            name='Plans',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_name', models.CharField(max_length=100)),
                ('plan_description', models.TextField(max_length=30)),
                ('widgets', models.IntegerField()),
                ('users', models.IntegerField()),
                ('calls', models.IntegerField()),
                ('razor_pay_planid', models.CharField(max_length=100)),
                ('admin_notes', models.TextField(max_length=30)),
            ],
        ),
    ]
