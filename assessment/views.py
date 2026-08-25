from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ChoiceAnswerForm, ConversationForm, SYMPTOMS, SymptomsForm
from .gemini import reflective_reply
from .models import Assessment, ConversationTurn


STEPS = {
    "focus": ("What would you like to explore?", Assessment.FOCUS_CHOICES, "focus"),
    "experience": ("Which experience best fits what you are dealing with?", Assessment.EXPERIENCE_CHOICES, "experience_category"),
    "safety": ("How safe do you feel right now?", Assessment.SAFETY_CHOICES, "safety_status"),
    "impact": ("How much is this affecting your day-to-day life?", Assessment.IMPACT_CHOICES, "daily_impact"),
    "support": ("Do you have someone you can contact for support today?", Assessment.SUPPORT_CHOICES, "support_system"),
}
NEXT_STEP = {"focus": "experience", "experience": "safety", "safety": "symptoms", "impact": "support", "support": "summary"}
REQUIRED = ("focus", "experience_category", "safety_status", "symptoms", "daily_impact", "support_system")


def home(request):
    return render(request, "assessment/home.html")


def _draft(request):
    assessment_id = request.session.get("assessment_id")
    if assessment_id:
        return Assessment.objects.filter(pk=assessment_id, status=Assessment.Status.IN_PROGRESS).first()
    return None


def _require_draft(request, prerequisite=None):
    assessment = _draft(request)
    if not assessment or (prerequisite and not getattr(assessment, prerequisite)):
        return None
    return assessment


def choice_step(request, step):
    question, choices, field = STEPS[step]
    assessment = _draft(request)
    if step != "focus" and not assessment:
        return redirect("focus")
    if request.method == "POST":
        form = ChoiceAnswerForm(request.POST, choices=choices)
        if form.is_valid():
            if not assessment:
                assessment = Assessment.objects.create()
                request.session["assessment_id"] = assessment.pk
            setattr(assessment, field, form.cleaned_data["value"])
            assessment.full_clean(exclude=[name for name in REQUIRED if name != field])
            assessment.save(update_fields=[field])
            if step == "safety" and assessment.safety_status == "unsafe":
                return redirect("safety_support")
            return redirect(NEXT_STEP[step])
    else:
        initial = {"value": getattr(assessment, field, "")} if assessment else None
        form = ChoiceAnswerForm(initial=initial, choices=choices)
    return render(request, "assessment/step.html", {"question": question, "form": form, "step": step})


def safety_support(request):
    assessment = _require_draft(request, "safety_status")
    if not assessment or assessment.safety_status != "unsafe":
        return redirect("safety")
    return render(request, "assessment/safety_support.html", {"assessment": assessment})


def symptoms(request):
    assessment = _require_draft(request, "safety_status")
    if not assessment:
        return redirect("safety")
    if request.method == "POST":
        form = SymptomsForm(request.POST)
        if form.is_valid():
            assessment.symptoms = form.cleaned_data["symptoms"]
            assessment.full_clean(exclude=[name for name in REQUIRED if name != "symptoms"])
            assessment.save(update_fields=["symptoms"])
            return redirect("impact")
    else:
        form = SymptomsForm(initial={"symptoms": assessment.symptoms})
    return render(request, "assessment/symptoms.html", {"form": form, "symptoms": SYMPTOMS})


def summary(request):
    assessment = _draft(request)
    if not assessment or any(not getattr(assessment, field) for field in REQUIRED):
        return redirect("focus")
    if request.method == "POST":
        assessment.status = Assessment.Status.COMPLETED
        assessment.completed_at = timezone.now()
        assessment.full_clean()
        assessment.save(update_fields=["status", "completed_at"])
        request.session.pop("assessment_id", None)
        return render(request, "assessment/complete.html", {"assessment": assessment, "urgent": assessment.safety_status == "unsafe"})
    return render(request, "assessment/summary.html", {"assessment": assessment, "symptom_labels": [dict(SYMPTOMS)[item] for item in assessment.symptoms], "urgent": assessment.safety_status == "unsafe"})


@require_POST
def conversation(request, assessment_id):
    assessment = get_object_or_404(Assessment, pk=assessment_id, status=Assessment.Status.COMPLETED)
    form = ConversationForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Enter a message of up to 1,500 characters."}, status=400)
    text = form.cleaned_data["message"]
    user_turn = ConversationTurn.objects.create(assessment=assessment, role="user", content=text)
    history = list(assessment.conversation_turns.values("role", "content"))
    reply = reflective_reply(assessment, history, user_turn.content)
    assistant_text = " ".join(filter(None, [reply["reflection"], "Reported patterns: " + "; ".join(reply["reported_patterns"]) if reply["reported_patterns"] else "", reply["follow_up_question"]]))
    ConversationTurn.objects.create(assessment=assessment, role="assistant", content=assistant_text)
    return JsonResponse({"reply": reply, "notice": "This conversation is reflective support, not a diagnosis or emergency service."})
