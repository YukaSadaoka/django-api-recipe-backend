# Generated by Django 2.1.15 on 2020-12-24 03:40

import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auto_20201224_0311'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='image',
            field=models.ImageField(null=True, upload_to=core.models.article_image_file_path),
        ),
    ]
