from django.core.validators import MaxLengthValidator
from django.conf import settings
from django.db import models


class Assessment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessments")

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


class AssessmentAnswer(models.Model):
    """An auditable answer record; values are always selected by server-side forms."""
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="answers")
    question_key = models.SlugField(max_length=64)
    question_text = models.CharField(max_length=500)
    answer = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("assessment", "question_key"), name="one_answer_per_question")]
        ordering = ["created_at"]


class SymptomReport(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="symptom_reports")
    symptom = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("assessment", "symptom"), name="one_report_per_symptom")]


class ConversationTurn(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="conversation_turns")
    role = models.CharField(max_length=10, choices=(("user", "User"), ("assistant", "Assistant")))
    content = models.TextField(validators=[MaxLengthValidator(1500)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class DoctorProfile(models.Model):
    """Marks an account as a clinician who can review assigned patients only."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_profile")
    display_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.display_name or self.user.get_username()


class CareAssignment(models.Model):
    """An administrator-controlled link between one patient and one doctor."""
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="care_assignments")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="patient_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("patient", "doctor"), name="one_doctor_assignment_per_patient")]
        ordering = ["patient__username"]

    def __str__(self):
        return f"{self.patient.get_username()} → {self.doctor}"
