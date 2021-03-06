# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-03-08 20:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('foias', '0021_foia_response_satisfactory'),
    ]

    operations = [
        migrations.AddField(
            model_name='foia',
            name='last_notified',
            field=models.DateField(null=True, verbose_name='most recent date notified'),
        ),
        migrations.AlterField(
            model_name='foia',
            name='reporter',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='foias.MyUser', verbose_name='Who filed this request?'),
        ),
    ]
