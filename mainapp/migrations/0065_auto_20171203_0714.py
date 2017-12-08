# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-12-03 07:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0064_auto_20171202_1251'),
    ]

    operations = [
        migrations.AddField(
            model_name='widget',
            name='appearance_alert_background',
            field=models.CharField(default='white', max_length=10),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_alert_textcolor',
            field=models.CharField(default='black', max_length=10),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_alerttext',
            field=models.CharField(default='Hey There! Would You Like To Receive A Call From Us Right Now ?', max_length=100),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_body_background',
            field=models.CharField(default='white', max_length=10),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_body_textcolor',
            field=models.CharField(default='black', max_length=10),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_buttonimage',
            field=models.CharField(default='button1.gif', max_length=10),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_calltext',
            field=models.CharField(default='Would You Like To Receive A Call From Us Right Now ?', max_length=100),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_leadtext',
            field=models.CharField(default='We Are Not Around. Please Leave Your Number To Receive A Callback Soon', max_length=100),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_leadthankyoutext',
            field=models.CharField(default='Thank you, we will get in touch with you soon', max_length=100),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_playsoundonalert',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_position',
            field=models.CharField(default='right', max_length=10),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_showalert',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='widget',
            name='appearance_showalert_after',
            field=models.IntegerField(default=3000),
        ),
    ]