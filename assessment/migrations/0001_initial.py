from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(name="Assessment", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("focus", models.CharField(max_length=20)), ("experience_category", models.CharField(max_length=30)), ("safety_status", models.CharField(max_length=10)), ("symptoms", models.JSONField(default=list)), ("daily_impact", models.CharField(max_length=20)), ("support_system", models.CharField(max_length=10)), ("created_at", models.DateTimeField(auto_now_add=True))], options={"ordering": ["-created_at"]})]
