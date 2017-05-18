# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-17 22:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foias', '0003_auto_20170217_2245'),
    ]

    operations = [
        migrations.AlterField(
            model_name='foia',
            name='ack_date',
            field=models.DateField(blank=True, null=True, verbose_name='date acknowledgement letter received'),
        ),
        migrations.AlterField(
            model_name='foia',
            name='appeal_date',
            field=models.DateField(blank=True, null=True, verbose_name='date appeal filed'),
        ),
        migrations.AlterField(
            model_name='foia',
            name='resp_date',
            field=models.DateField(blank=True, null=True, verbose_name='date response received'),
        ),
    ]