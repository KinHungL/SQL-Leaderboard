# Generated by Django 4.0.3 on 2022-03-28 17:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task', '0004_querytask_query_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='querytask',
            name='error_message',
            field=models.TextField(null=True),
        ),
    ]