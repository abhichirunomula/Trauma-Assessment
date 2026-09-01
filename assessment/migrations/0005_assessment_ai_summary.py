from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0004_doctorprofile_careassignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessment',
            name='ai_summary',
            field=models.JSONField(blank=True, default=None, null=True),
        ),
    ]
