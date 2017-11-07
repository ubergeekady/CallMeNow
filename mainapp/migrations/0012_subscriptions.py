# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-02 18:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0011_auto_20171102_1644'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscriptions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('planid', models.IntegerField()),
                ('razorpay_subscription_id', models.CharField(max_length=100)),
                ('current_state', models.CharField(max_length=100)),
                ('accountid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mainapp.Accounts')),
            ],
        ),
    ]