from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.sign_in, name="login"),
    path("logout/", views.sign_out, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("assessment/focus/", views.choice_step, {"step": "focus"}, name="focus"),
    path("assessment/experience/", views.choice_step, {"step": "experience"}, name="experience"),
    path("assessment/safety/", views.choice_step, {"step": "safety"}, name="safety"),
    path("assessment/safety-support/", views.safety_support, name="safety_support"),
    path("assessment/symptoms/", views.symptoms, name="symptoms"),
    path("assessment/follow-up/", views.adaptive_question, name="adaptive_question"),
    path("assessment/impact/", views.choice_step, {"step": "impact"}, name="impact"),
    path("assessment/support/", views.choice_step, {"step": "support"}, name="support"),
    path("assessment/summary/", views.summary, name="summary"),
    path("assessment/<int:assessment_id>/conversation/", views.conversation, name="conversation"),
]
