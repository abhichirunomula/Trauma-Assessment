from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_owner(apps, schema_editor):
    """Existing anonymous records are retained under an unusable legacy account."""
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    Assessment = apps.get_model("assessment", "Assessment")
    owner, created = User.objects.get_or_create(username="legacy_assessment_owner")
    if created:
        owner.password = make_password(None)
        owner.save(update_fields=["password"])
    Assessment.objects.filter(user__isnull=True).update(user=owner)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("assessment", "0002_assessment_state_and_conversation"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessment",
            name="user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="assessments", to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(assign_legacy_owner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="assessment",
            name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessments", to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name="AssessmentAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_key", models.SlugField(max_length=64)),
                ("question_text", models.CharField(max_length=500)),
                ("answer", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="assessment.assessment")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="SymptomReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symptom", models.CharField(max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="symptom_reports", to="assessment.assessment")),
            ],
        ),
        migrations.AddConstraint(model_name="assessmentanswer", constraint=models.UniqueConstraint(fields=("assessment", "question_key"), name="one_answer_per_question")),
        migrations.AddConstraint(model_name="symptomreport", constraint=models.UniqueConstraint(fields=("assessment", "symptom"), name="one_report_per_symptom")),
    ]
