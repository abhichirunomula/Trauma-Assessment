from django.contrib import admin
from .models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "focus", "safety_status", "daily_impact", "support_system", "created_at")

# Register your models here.
