from django.core.validators import MaxLengthValidator
from django.db import models


class Assessment(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    FOCUS_CHOICES = (("physical", "Physical wellbeing"), ("mental", "Mental wellbeing"), ("both", "Both"))
    EXPERIENCE_CHOICES = (("recent_event", "A recent difficult event"), ("ongoing_stress", "Ongoing stress or pressure"), ("past_experience", "A past experience"), ("prefer_not_to_say", "Prefer not to say"))
    SAFETY_CHOICES = (("safe", "I feel safe"), ("unsure", "I feel unsure or unsettled"), ("unsafe", "I do not feel safe"))
    IMPACT_CHOICES = (("not_at_all", "Not at all"), ("a_little", "A little"), ("moderately", "Moderately"), ("a_lot", "A lot"))
    SUPPORT_CHOICES = (("yes", "Yes, I do"), ("not_sure", "I'm not sure"), ("no", "No, I don't"))

    focus = models.CharField(max_length=20, choices=FOCUS_CHOICES, blank=True)
    experience_category = models.CharField(max_length=30, choices=EXPERIENCE_CHOICES, blank=True)
    safety_status = models.CharField(max_length=10, choices=SAFETY_CHOICES, blank=True)
    symptoms = models.JSONField(default=list, blank=True)
    daily_impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, blank=True)
    support_system = models.CharField(max_length=10, choices=SUPPORT_CHOICES, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ConversationTurn(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="conversation_turns")
    role = models.CharField(max_length=10, choices=(("user", "User"), ("assistant", "Assistant")))
    content = models.TextField(validators=[MaxLengthValidator(1500)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
