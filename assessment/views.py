from django.contrib.auth import login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AdaptiveAnswerForm, CareAssignmentForm, ChoiceAnswerForm, ConversationForm, RegisterForm, SYMPTOMS, SignInForm, SymptomsForm
from .gemini import reflective_reply
from .llm import personalized_summary
from .models import Assessment, AssessmentAnswer, CareAssignment, ConversationTurn, SymptomReport

STEPS = {"focus": ("What would you like to explore?", Assessment.FOCUS_CHOICES, "focus"), "experience": ("Which experience best fits what you are dealing with?", Assessment.EXPERIENCE_CHOICES, "experience_category"), "safety": ("How safe do you feel right now?", Assessment.SAFETY_CHOICES, "safety_status"), "impact": ("How much is this affecting your day-to-day life?", Assessment.IMPACT_CHOICES, "daily_impact"), "support": ("Do you have someone you can contact for support today?", Assessment.SUPPORT_CHOICES, "support_system")}
NEXT_STEP = {"focus": "experience", "experience": "safety", "safety": "symptoms", "impact": "support", "support": "summary"}
REQUIRED = ("focus", "experience_category", "safety_status", "symptoms", "daily_impact", "support_system")
SAFETY_TERMS = ("kill myself", "suicide", "end my life", "hurt myself", "self harm", "harm myself", "immediate danger")


def _save_answer(assessment, key, question, answer):
    AssessmentAnswer.objects.update_or_create(assessment=assessment, question_key=key, defaults={"question_text": question, "answer": {"value": answer}})


def _adaptive_question(assessment):
    """A controlled, server-owned catalog decides every follow-up question."""
    symptoms = set(assessment.symptoms)
    catalog = (
        ("sleep", "adaptive_sleep", "When sleep is difficult, which approach feels most manageable?", (("routine", "A small wind-down routine"), ("environment", "Making my space more restful"), ("support", "Talking it through with someone"))),
        ("anxiety", "adaptive_anxiety", "When you feel on edge, what would feel most helpful to try?", (("pause", "A brief pause or grounding exercise"), ("plan", "Breaking one task into a smaller step"), ("support", "Reaching out to someone"))),
        ("low_mood", "adaptive_mood", "What is one gentle source of support you might be open to?", (("connection", "Connecting with a trusted person"), ("activity", "A small activity I usually value"), ("professional", "Learning about professional support"))),
        ("pain", "adaptive_discomfort", "What feels like a supportive next step for the discomfort you reported?", (("rest", "Giving myself rest or a pause"), ("tracking", "Noticing when it is better or worse"), ("professional", "Considering a healthcare professional"))),
    )
    for symptom, key, question, choices in catalog:
        if symptom in symptoms:
            return key, question, choices
    return "adaptive_support", "What would make the next few days feel a little more supported?", (("routine", "A small routine"), ("connection", "Connection with someone I trust"), ("information", "Finding helpful information or services"))


def home(request):
    return redirect("dashboard") if request.user.is_authenticated else render(request, "assessment/home.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


def _portal_for(user):
    if user.is_staff:
        return "admin"
    if getattr(user, "doctor_profile", None):
        return "doctor"
    return "patient"


def sign_in(request, portal=None):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignInForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        actual_portal = _portal_for(user)
        if portal and actual_portal != portal:
            form.add_error(None, f"This account belongs to the {actual_portal} portal. Please use the correct sign-in page.")
        else:
            login(request, user)
            return redirect(request.POST.get("next") or "dashboard")
    labels = {"patient": "Patient", "doctor": "Doctor", "admin": "Administrator"}
    return render(request, "registration/login.html", {"form": form, "portal": portal, "portal_label": labels.get(portal, "")})


@require_POST
def sign_out(request):
    logout(request)
    return redirect("home")


@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect("admin_dashboard")
    if getattr(request.user, "doctor_profile", None):
        return redirect("doctor_dashboard")
    assessments = request.user.assessments.all().prefetch_related("symptom_reports")
    return render(request, "assessment/dashboard.html", {"assessments": assessments, "latest": assessments.first()})


@login_required
def doctor_dashboard(request):
    doctor = getattr(request.user, "doctor_profile", None)
    if not doctor:
        raise PermissionDenied("This area is for assigned doctors only.")
    assignments = CareAssignment.objects.filter(doctor=doctor).select_related("patient").prefetch_related("patient__assessments")
    return render(request, "assessment/doctor_dashboard.html", {"assignments": assignments, "doctor": doctor})


@login_required
def doctor_patient_detail(request, patient_id):
    doctor = getattr(request.user, "doctor_profile", None)
    if not doctor:
        raise PermissionDenied("This area is for assigned doctors only.")
    assignment = get_object_or_404(CareAssignment.objects.select_related("patient"), doctor=doctor, patient_id=patient_id)
    assessments = Assessment.objects.filter(user=assignment.patient).prefetch_related("answers", "conversation_turns", "symptom_reports")
    return render(request, "assessment/doctor_patient_detail.html", {"patient": assignment.patient, "assessments": assessments})


@staff_member_required
def admin_dashboard(request):
    form = CareAssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        assignment, created = CareAssignment.objects.get_or_create(
            patient=form.cleaned_data["patient"], doctor=form.cleaned_data["doctor"]
        )
        if not created:
            form.add_error(None, "That patient is already assigned to this doctor.")
        else:
            return redirect("admin_dashboard")
    assignments = CareAssignment.objects.select_related("patient", "doctor__user")
    return render(request, "assessment/admin_dashboard.html", {"form": form, "assignments": assignments})


def _draft(request):
    assessment_id = request.session.get("assessment_id")
    return Assessment.objects.filter(pk=assessment_id, user=request.user, status=Assessment.Status.IN_PROGRESS).first() if assessment_id else None


@login_required
def choice_step(request, step):
    question, choices, field = STEPS[step]
    assessment = _draft(request)
    if step != "focus" and not assessment:
        return redirect("focus")
    form = ChoiceAnswerForm(request.POST or None, initial={"value": getattr(assessment, field, "")} if assessment else None, choices=choices)
    if request.method == "POST" and form.is_valid():
        if not assessment:
            assessment = Assessment.objects.create(user=request.user)
            request.session["assessment_id"] = assessment.pk
        value = form.cleaned_data["value"]
        setattr(assessment, field, value)
        assessment.full_clean(exclude=[name for name in REQUIRED if name != field])
        assessment.save(update_fields=[field])
        _save_answer(assessment, step, question, value)
        if step == "safety" and value == "unsafe":
            return redirect("safety_support")
        return redirect(NEXT_STEP[step])
    return render(request, "assessment/step.html", {"question": question, "form": form, "step": step})


@login_required
def safety_support(request):
    assessment = _draft(request)
    if not assessment or assessment.safety_status != "unsafe":
        return redirect("safety")
    return render(request, "assessment/safety_support.html", {"assessment": assessment})


@login_required
def symptoms(request):
    assessment = _draft(request)
    if not assessment or not assessment.safety_status:
        return redirect("safety")
    form = SymptomsForm(request.POST or None, initial={"symptoms": assessment.symptoms})
    if request.method == "POST" and form.is_valid():
        values = form.cleaned_data["symptoms"]
        with transaction.atomic():
            assessment.symptoms = values
            assessment.full_clean(exclude=[name for name in REQUIRED if name != "symptoms"])
            assessment.save(update_fields=["symptoms"])
            SymptomReport.objects.filter(assessment=assessment).delete()
            SymptomReport.objects.bulk_create([SymptomReport(assessment=assessment, symptom=value) for value in values])
            _save_answer(assessment, "symptoms", "Which changes have you noticed?", values)
        return redirect("adaptive_question")
    return render(request, "assessment/symptoms.html", {"form": form, "symptoms": SYMPTOMS})


@login_required
def adaptive_question(request):
    assessment = _draft(request)
    if not assessment or not assessment.symptoms:
        return redirect("symptoms")
    key, question, choices = _adaptive_question(assessment)
    prior = assessment.answers.filter(question_key=key).first()
    form = AdaptiveAnswerForm(request.POST or None, initial={"value": prior.answer.get("value") if prior else ""}, choices=choices)
    if request.method == "POST" and form.is_valid():
        _save_answer(assessment, key, question, form.cleaned_data["value"] or "skipped")
        return redirect("impact")
    return render(request, "assessment/adaptive_question.html", {"question": question, "form": form})


@login_required
def summary(request):
    assessment = _draft(request)
    if not assessment or any(not getattr(assessment, field) for field in REQUIRED):
        return redirect("focus")
    if not assessment.ai_summary:
        assessment.ai_summary = personalized_summary(assessment)
        assessment.save(update_fields=["ai_summary"])
    if request.method == "POST":
        assessment.status, assessment.completed_at = Assessment.Status.COMPLETED, timezone.now()
        assessment.full_clean()
        assessment.save(update_fields=["status", "completed_at"])
        request.session.pop("assessment_id", None)
        return render(request, "assessment/complete.html", {"assessment": assessment, "ai_summary": assessment.ai_summary, "urgent": assessment.safety_status == "unsafe"})
    return render(request, "assessment/summary.html", {"assessment": assessment, "ai_summary": assessment.ai_summary, "symptom_labels": [dict(SYMPTOMS)[item] for item in assessment.symptoms], "urgent": assessment.safety_status == "unsafe"})


@login_required
@require_POST
def conversation(request, assessment_id):
    assessment = get_object_or_404(Assessment, pk=assessment_id, user=request.user, status=Assessment.Status.COMPLETED)
    form = ConversationForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Enter a message of up to 1,500 characters."}, status=400)
    user_text = form.cleaned_data["message"]
    if any(term in user_text.lower() for term in SAFETY_TERMS):
        ConversationTurn.objects.create(assessment=assessment, role="user", content=user_text)
        text = "I’m really glad you said that. Please contact your local emergency number or crisis service now, or reach a trusted person who can stay with you."
        ConversationTurn.objects.create(assessment=assessment, role="assistant", content=text)
        return JsonResponse({"reply": {"reflection": text, "reported_patterns": [], "follow_up_question": "Are you able to contact someone nearby right now?", "provider": "safety"}, "notice": "This service cannot provide emergency support."})
    user_turn = ConversationTurn.objects.create(assessment=assessment, role="user", content=user_text)
    reply = reflective_reply(assessment, list(assessment.conversation_turns.values("role", "content")), user_turn.content)
    assistant_text = " ".join(filter(None, [reply["reflection"], "Reported patterns: " + "; ".join(reply["reported_patterns"]) if reply["reported_patterns"] else "", reply["follow_up_question"]]))
    ConversationTurn.objects.create(assessment=assessment, role="assistant", content=assistant_text)
    return JsonResponse({"reply": reply, "notice": "This conversation is reflective support, not a diagnosis or emergency service."})
