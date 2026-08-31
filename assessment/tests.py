from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Assessment, CareAssignment, ConversationTurn, DoctorProfile


class AssessmentEngineTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="river", password="safe-password-123")
        self.client.force_login(self.user)

    def answer(self, route, key, value):
        return self.client.post(reverse(route), {key: value}, follow=True)

    def complete(self, safety="safe"):
        self.answer("focus", "value", "both")
        self.answer("experience", "value", "ongoing_stress")
        self.answer("safety", "value", safety)
        if safety == "unsafe":
            self.client.get(reverse("safety_support"))
        self.answer("symptoms", "symptoms", ["sleep", "energy"])
        self.answer("adaptive_question", "value", "routine")
        self.answer("impact", "value", "moderately")
        self.answer("support", "value", "yes")
        return self.client.post(reverse("summary"), follow=True)

    def test_every_answer_is_persisted_before_completion(self):
        self.answer("focus", "value", "physical")
        assessment = Assessment.objects.get()
        self.assertEqual(assessment.user, self.user)
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
        self.assertEqual(assessment.answers.count(), 7)

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


class DoctorReviewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.patient = User.objects.create_user(username="patient-one", password="safe-password-123")
        self.doctor_user = User.objects.create_user(username="doctor-one", password="safe-password-123")
        self.other_doctor_user = User.objects.create_user(username="doctor-two", password="safe-password-123")
        self.doctor = DoctorProfile.objects.create(user=self.doctor_user, display_name="Dr One")
        self.other_doctor = DoctorProfile.objects.create(user=self.other_doctor_user, display_name="Dr Two")
        self.assessment = Assessment.objects.create(user=self.patient, focus="mental", safety_status="safe", status=Assessment.Status.COMPLETED)

    def test_assigned_doctor_can_review_patient_responses(self):
        CareAssignment.objects.create(patient=self.patient, doctor=self.doctor)
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("doctor_patient_detail", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "patient-one")

    def test_unassigned_doctor_cannot_review_patient(self):
        CareAssignment.objects.create(patient=self.patient, doctor=self.doctor)
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("doctor_patient_detail", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 404)

    def test_patient_cannot_open_doctor_dashboard(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("doctor_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_patient_is_redirected_to_patient_dashboard(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your private check-in space")

    def test_admin_can_open_assignment_dashboard(self):
        admin = get_user_model().objects.create_user(username="admin-one", password="safe-password-123", is_staff=True)
        self.client.force_login(admin)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Patient care assignments")

    def test_role_specific_login_rejects_wrong_portal(self):
        response = self.client.post(reverse("doctor_login"), {"username": "patient-one", "password": "safe-password-123"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "belongs to the patient portal")
