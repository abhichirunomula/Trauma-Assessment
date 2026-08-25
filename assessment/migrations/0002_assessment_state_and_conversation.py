from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assessment", "0001_initial")]
    operations = [
        migrations.AlterField(model_name="assessment", name="focus", field=models.CharField(blank=True, choices=[("physical", "Physical wellbeing"), ("mental", "Mental wellbeing"), ("both", "Both")], max_length=20)),
        migrations.AlterField(model_name="assessment", name="experience_category", field=models.CharField(blank=True, choices=[("recent_event", "A recent difficult event"), ("ongoing_stress", "Ongoing stress or pressure"), ("past_experience", "A past experience"), ("prefer_not_to_say", "Prefer not to say")], max_length=30)),
        migrations.AlterField(model_name="assessment", name="safety_status", field=models.CharField(blank=True, choices=[("safe", "I feel safe"), ("unsure", "I feel unsure or unsettled"), ("unsafe", "I do not feel safe")], max_length=10)),
        migrations.AlterField(model_name="assessment", name="daily_impact", field=models.CharField(blank=True, choices=[("not_at_all", "Not at all"), ("a_little", "A little"), ("moderately", "Moderately"), ("a_lot", "A lot")], max_length=20)),
        migrations.AlterField(model_name="assessment", name="support_system", field=models.CharField(blank=True, choices=[("yes", "Yes, I do"), ("not_sure", "I'm not sure"), ("no", "No, I don't")], max_length=10)),
        migrations.AddField(model_name="assessment", name="completed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="assessment", name="status", field=models.CharField(choices=[("in_progress", "In progress"), ("completed", "Completed")], default="in_progress", max_length=20)),
        migrations.CreateModel(name="ConversationTurn", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant")], max_length=10)), ("content", models.TextField()), ("created_at", models.DateTimeField(auto_now_add=True)), ("assessment", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="conversation_turns", to="assessment.assessment"))], options={"ordering": ["created_at"]}),
    ]
