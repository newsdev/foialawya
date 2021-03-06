# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-27 19:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foias', '0014_auto_20170222_1918'),
    ]

    operations = [
        migrations.AddField(
            model_name='foia',
            name='date_response_due_custom',
            field=models.DateField(blank=True, null=True, verbose_name='Did the agency tell you when to expect the records?'),
        ),
        migrations.AlterField(
            model_name='foia',
            name='submission_notes',
            field=models.TextField(blank=True, verbose_name="notes about acknowledgement (did they respond by mail or email? do you have a phone number? did they tell you what track it's on?)"),
        ),
    ]
