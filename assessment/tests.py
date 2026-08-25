from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import Assessment, ConversationTurn


class AssessmentEngineTests(TestCase):
    def answer(self, route, key, value):
        return self.client.post(reverse(route), {key: value}, follow=True)

    def complete(self, safety="safe"):
        self.answer("focus", "value", "both")
        self.answer("experience", "value", "ongoing_stress")
        self.answer("safety", "value", safety)
        if safety == "unsafe":
            self.client.get(reverse("safety_support"))
        self.answer("symptoms", "symptoms", ["sleep", "energy"])
        self.answer("impact", "value", "moderately")
        self.answer("support", "value", "yes")
        return self.client.post(reverse("summary"), follow=True)

    def test_every_answer_is_persisted_before_completion(self):
        self.answer("focus", "value", "physical")
        assessment = Assessment.objects.get()
        self.assertEqual(assessment.focus, "physical")
        self.assertEqual(assessment.status, Assessment.Status.IN_PROGRESS)
        self.answer("experience", "value", "recent_event")
        self.assertEqual(Assessment.objects.get().experience_category, "recent_event")

    def test_complete_pipeline_validates_and_completes_record(self):
        response = self.complete()
        self.assertContains(response, "CHECK-IN SAVED")
        assessment = Assessment.objects.get()
        self.assertEqual(assessment.status, Assessment.Status.COMPLETED)
        self.assertIsNotNone(assessment.completed_at)
        self.assertEqual(assessment.symptoms, ["sleep", "energy"])

    def test_unsafe_response_uses_dedicated_safety_layer(self):
        self.answer("focus", "value", "mental")
        self.answer("experience", "value", "recent_event")
        response = self.client.post(reverse("safety"), {"value": "unsafe"})
        self.assertRedirects(response, reverse("safety_support"))
        self.assertEqual(Assessment.objects.get().safety_status, "unsafe")

    def test_invalid_choice_is_not_saved(self):
        response = self.client.post(reverse("focus"), {"value": "invalid"})
        self.assertContains(response, "Choose one option")
        self.assertEqual(Assessment.objects.count(), 0)

    @patch("assessment.views.reflective_reply")
    def test_conversation_saves_turns_and_returns_guarded_output(self, reply):
        self.complete()
        assessment = Assessment.objects.get()
        reply.return_value = {"reflection": "You mentioned disrupted sleep.", "reported_patterns": ["Reported disrupted sleep during ongoing stress."], "follow_up_question": "What helps you rest?", "provider": "gemini"}
        response = self.client.post(reverse("conversation", args=[assessment.pk]), {"message": "I have not been sleeping well."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConversationTurn.objects.filter(assessment=assessment).count(), 2)
        self.assertEqual(response.json()["reply"]["provider"], "gemini")
