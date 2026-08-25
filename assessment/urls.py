from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("assessment/focus/", views.choice_step, {"step": "focus"}, name="focus"),
    path("assessment/experience/", views.choice_step, {"step": "experience"}, name="experience"),
    path("assessment/safety/", views.choice_step, {"step": "safety"}, name="safety"),
    path("assessment/safety-support/", views.safety_support, name="safety_support"),
    path("assessment/symptoms/", views.symptoms, name="symptoms"),
    path("assessment/impact/", views.choice_step, {"step": "impact"}, name="impact"),
    path("assessment/support/", views.choice_step, {"step": "support"}, name="support"),
    path("assessment/summary/", views.summary, name="summary"),
    path("assessment/<int:assessment_id>/conversation/", views.conversation, name="conversation"),
]
