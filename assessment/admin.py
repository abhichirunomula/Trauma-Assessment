from django.contrib import admin
from .models import Assessment, AssessmentAnswer, CareAssignment, ConversationTurn, DoctorProfile, SymptomReport


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "focus", "safety_status", "daily_impact", "support_system", "created_at")
    list_select_related = ("user",)


admin.site.register(AssessmentAnswer)
admin.site.register(SymptomReport)
admin.site.register(ConversationTurn)


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name")
    search_fields = ("user__username", "display_name")


@admin.register(CareAssignment)
class CareAssignmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "assigned_at")
    list_select_related = ("patient", "doctor__user")
    search_fields = ("patient__username", "doctor__user__username", "doctor__display_name")
    autocomplete_fields = ("patient", "doctor")

# Register your models here.
