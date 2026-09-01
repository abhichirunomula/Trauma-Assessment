"""Provider-agnostic LLM layer for the personalized check-in guidance.

OpenAI is the default provider; Gemini and a safe local fallback are also
supported. Every response is validated against the same guardrails: no
diagnosis, no disorder names, no medication advice, no claims of a cure, and a
consistent ``{situation, suggestions, professional_support}`` output contract.
"""
import json

from django.conf import settings


SYSTEM_INSTRUCTION = (
    "You are a supportive wellbeing companion. Based only on the structured "
    "answers a person just gave, write brief, practical self-care guidance. "
    "Reflect their situation in one or two plain sentences grounded in their own "
    "statements. Then give 3 to 5 concrete, gentle coping suggestions tailored "
    "to the changes they reported (for example: sleep routine, grounding or "
    "breathing exercises, gentle movement, reaching out to a trusted person, "
    "pacing tasks). Finally, give short guidance on when and how to seek "
    "professional support. Do NOT diagnose, name a disorder, identify root "
    "causes, recommend or adjust medication, or promise a cure or a guaranteed "
    "outcome. Do not assess imminent safety; the application handles that "
    "separately. Keep every sentence short and warm. "
    'Respond with a JSON object of the form {"situation": string, '
    '"suggestions": [string], "professional_support": string}.'
)

BANNED_TERMS = ("root cause", "you have a", "diagnosed with", "your diagnosis", "guaranteed to", "will cure")

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "situation": {"type": "string"},
        "suggestions": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "professional_support": {"type": "string"},
    },
    "required": ["situation", "suggestions", "professional_support"],
}

# Generic, non-clinical self-care tips keyed by reported symptom, used for the
# local fallback so the page always shows tailored guidance.
_SYMPTOM_TIPS = {
    "sleep": "Keep a consistent wind-down routine and a screen-free 30 minutes before bed.",
    "anxiety": "When you feel on edge, try slow breathing or the 5-4-3-2-1 grounding exercise.",
    "low_mood": "Aim for one small activity you usually value, and connect with someone you trust.",
    "concentration": "Break one task into a single small step and work in short, focused blocks.",
    "pain": "Build in short rest breaks and gentle movement, and note when it eases or worsens.",
    "energy": "Protect regular meals and a steady sleep schedule, and pace demanding tasks across the day.",
    "appetite": "Try small, regular meals or snacks even when appetite is low, and keep easy foods to hand.",
}


def build_context(assessment):
    """Minimize data sent to the provider: no identity, ids, or timestamps."""
    return {
        "assessment": {
            "focus": assessment.focus,
            "experience": assessment.experience_category,
            "symptoms": assessment.symptoms,
            "daily_impact": assessment.daily_impact,
            "support_available": assessment.support_system,
            "curated_follow_up_answers": [
                {"question": answer.question_text, "answer": answer.answer}
                for answer in assessment.answers.filter(question_key__startswith="adaptive_")
            ],
        },
    }


def personalized_summary(assessment):
    """Return validated structured guidance, or a safe local fallback."""
    provider = getattr(settings, "LLM_PROVIDER", "openai")
    context = build_context(assessment)
    try:
        if provider == "openai":
            data = _openai_reply(context)
        elif provider == "gemini":
            data = _gemini_reply(context)
        else:
            return _fallback(assessment)
    except Exception:
        return _fallback(assessment)
    if data is None:
        return _fallback(assessment)
    return _validate(data, provider, assessment)


def _openai_reply(context):
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return None
    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=15)
    response = client.chat.completions.create(
        model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": json.dumps(context)},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    return json.loads(response.choices[0].message.content)


def _gemini_reply(context):
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return None
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
        contents=json.dumps(context),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        ),
    )
    return json.loads(response.text)


def _validate(data, provider, assessment):
    situation = str(data.get("situation", ""))[:600]
    suggestions = [str(item)[:240] for item in data.get("suggestions", [])[:5] if str(item).strip()]
    professional = str(data.get("professional_support", ""))[:600]
    haystack = f"{situation} {' '.join(suggestions)} {professional}".lower()
    if not situation or len(suggestions) < 2 or any(term in haystack for term in BANNED_TERMS):
        return _fallback(assessment)
    return {
        "situation": situation,
        "suggestions": suggestions,
        "professional_support": professional,
        "provider": provider,
    }


def _fallback(assessment=None):
    symptoms = list(getattr(assessment, "symptoms", []) or [])
    suggestions = [_SYMPTOM_TIPS[symptom] for symptom in symptoms if symptom in _SYMPTOM_TIPS]
    suggestions.append("Tell one trusted person how the past week has been for you.")
    if getattr(assessment, "support_system", "") in ("no", "not_sure"):
        suggestions.append("Look up one local support line or service you could contact if you need to.")
    if len(suggestions) < 3:
        suggestions.append("Give yourself permission to take the next few days one step at a time.")
    return {
        "situation": "Thank you for taking time to check in. What you shared about how you have been feeling matters.",
        "suggestions": suggestions[:5],
        "professional_support": (
            "If these feelings last more than a couple of weeks, get in the way of daily life, or feel like "
            "too much to manage alone, a GP or a licensed therapist can help you decide what support fits you."
        ),
        "provider": "local",
    }
