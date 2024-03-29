# Generated by Django 5.0.1 on 2024-03-27 09:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surApp', '0003_alter_voting_options_question_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('choice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_votes', to='surApp.choice')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_votes', to='surApp.question')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_votes', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.DeleteModel(
            name='Vote',
        ),
    ]
