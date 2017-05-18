# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-27 21:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('foias', '0017_auto_20170227_1528'),
    ]

    operations = [
        migrations.CreateModel(
            name='Agency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Agency Name')),
                ('notes', models.TextField(verbose_name='Notes about the agency')),
            ],
        ),
        migrations.AlterModelOptions(
            name='foia',
            options={'verbose_name': 'FOIA', 'verbose_name_plural': 'FOIAs'},
        ),
        migrations.AlterModelOptions(
            name='nytemployee',
            options={'verbose_name': 'NYT Employee', 'verbose_name_plural': 'NYT Employees'},
        ),
        migrations.AlterField(
            model_name='foia',
            name='agency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='foias.Agency'),
        ),
    ]