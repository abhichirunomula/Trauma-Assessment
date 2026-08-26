from django.contrib import admin
from .models import Assessment, AssessmentAnswer, ConversationTurn, SymptomReport


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "focus", "safety_status", "daily_impact", "support_system", "created_at")
    list_select_related = ("user",)


admin.site.register(AssessmentAnswer)
admin.site.register(SymptomReport)
admin.site.register(ConversationTurn)

# Register your models here.
