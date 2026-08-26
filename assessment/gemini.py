"""Guarded Gemini integration for reflective, non-clinical conversations."""
import json

from django.conf import settings


SYSTEM_INSTRUCTION = """You are a supportive wellbeing check-in companion. Ask one gentle, optional follow-up question. You may describe only reported patterns or possible contributing factors based on the user's own statements. Never diagnose, name a disorder, determine root causes, provide medical advice, or claim certainty. Do not assess imminent safety; the application handles safety separately. Use concise, plain language and include no more than two reported patterns."""


def build_context(assessment, history, user_message):
    """Minimize data sent to Gemini: no identity, ids, timestamps, or full history."""
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
        "recent_conversation": [{"role": item["role"], "content": item["content"]} for item in history[-4:]],
        "new_message": user_message,
    }


def reflective_reply(assessment, history, user_message):
    """Return validated structured output or a safe local fallback when Gemini is unavailable."""
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return _fallback()
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        context = build_context(assessment, history, user_message)
        response = client.models.generate_content(
            model=getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
            contents=json.dumps(context),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema={"type": "object", "properties": {"reflection": {"type": "string"}, "reported_patterns": {"type": "array", "items": {"type": "string"}, "maxItems": 2}, "follow_up_question": {"type": "string"}}, "required": ["reflection", "reported_patterns", "follow_up_question"]},
            ),
        )
        data = json.loads(response.text)
        return _validate(data)
    except Exception:
        return _fallback()


def _validate(data):
    reflection = str(data.get("reflection", ""))[:500]
    patterns = [str(item)[:180] for item in data.get("reported_patterns", [])[:2]]
    question = str(data.get("follow_up_question", ""))[:300]
    banned = ("diagnos", "root cause", "you have ", "disorder")
    if not reflection or not question or any(term in f"{reflection} {' '.join(patterns)} {question}".lower() for term in banned):
        return _fallback()
    return {"reflection": reflection, "reported_patterns": patterns, "follow_up_question": question, "provider": "gemini"}


def _fallback():
    return {"reflection": "Thank you for sharing that. Your experience matters, and you can take this one step at a time.", "reported_patterns": [], "follow_up_question": "What feels most important for you to have support with right now?", "provider": "local"}
