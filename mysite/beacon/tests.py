from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Course, Lesson, Enrolment  

User = get_user_model()


# ------------------------------
# STUDENT STORIES
# ------------------------------
class StudentAccountTests(TestCase):
    def test_student_can_create_account(self):
        response = self.client.post(reverse("sign_up"), {
            "email": "stud@test.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
            "role": "STUDENT",
            "first_name": "Kai",
            "last_name": "Bin",
            "title": "Mr"
        })
        # signup redirects to login after success
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="stud@test.com").exists())

    def test_student_can_login(self):
        User.objects.create_user(
            email="stud2@test.com", password="pass123", role="STUDENT"
        )
        response = self.client.post(reverse("login"), {
            "email": "stud2@test.com",
            "password": "pass123"
        })
        # should redirect to student_dashboard
        self.assertEqual(response.status_code, 302)


class StudentCourseTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            email="inst@test.com", password="pass123", role="INSTRUCTOR"
        )
        self.student = User.objects.create_user(
            email="stud@test.com", password="pass123", role="STUDENT"
        )
        self.course = Course.objects.create(
            course_id="C001", title="Test Course", instructor=self.instructor
        )

    def test_student_can_enroll_in_course(self):
        self.client.login(email="stud@test.com", password="pass123")
        response = self.client.get(reverse("enrol_course", args=[self.course.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.student, self.course.students.all())

    def test_student_can_view_courses(self):
        self.course.students.add(self.student)
        self.client.login(email="stud@test.com", password="pass123")
        response = self.client.get(reverse("student_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")


class StudentLessonTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            email="inst@test.com", password="pass123", role="INSTRUCTOR"
        )
        self.student = User.objects.create_user(
            email="stud@test.com", password="pass123", role="STUDENT"
        )
        self.course = Course.objects.create(
            course_id="C002", title="Lesson Course", instructor=self.instructor
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Lesson 1",
            description="desc",
            designer=self.instructor
        )

    def test_student_can_enroll_in_lesson(self):
        Enrolment.objects.create(student=self.student, lesson=self.lesson)
        self.assertTrue(
            Enrolment.objects.filter(student=self.student, lesson=self.lesson).exists()
        )

    def test_student_cannot_double_enroll(self):
        Enrolment.objects.create(student=self.student, lesson=self.lesson)
        with self.assertRaises(Exception):  # unique_together should block
            Enrolment.objects.create(student=self.student, lesson=self.lesson)


# ------------------------------
# INSTRUCTOR STORIES
# ------------------------------
class InstructorCourseTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            email="inst@test.com", password="pass123", role="INSTRUCTOR"
        )

    def test_instructor_can_login(self):
        response = self.client.post(reverse("instructor_login"), {
            "email": "inst@test.com",
            "password": "pass123"
        })
        # should redirect to instructor_dashboard
        self.assertEqual(response.status_code, 302)

    def test_instructor_can_create_course(self):
        self.client.login(email="inst@test.com", password="pass123")
        response = self.client.post(reverse("create_course"), {
            "course_id": "C010",
            "title": "New Course",
            "status": "active",
            "instructor": self.instructor.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(course_id="C010").exists())

    def test_instructor_can_edit_course(self):
        course = Course.objects.create(course_id="C011", title="Old Title", instructor=self.instructor)
        self.client.login(email="inst@test.com", password="pass123")
        response = self.client.post(reverse("edit_course", args=[course.id]), {
            "course_id": "C011",
            "title": "Updated Title",
            "status": "active",
            "instructor": self.instructor.id
        })
        self.assertEqual(response.status_code, 302)
        course.refresh_from_db()
        self.assertEqual(course.title, "Updated Title")

    def test_instructor_can_delete_course(self):
        course = Course.objects.create(course_id="C012", title="Temp Course", instructor=self.instructor)
        self.client.login(email="inst@test.com", password="pass123")
        response = self.client.get(reverse("delete_course", args=[course.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Course.objects.filter(course_id="C012").exists())


class InstructorLessonTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            email="inst2@test.com", password="pass123", role="INSTRUCTOR"
        )
        self.course = Course.objects.create(course_id="C020", title="Course for Lessons", instructor=self.instructor)

    def test_instructor_can_create_lesson(self):
        self.client.login(email="inst2@test.com", password="pass123")
        response = self.client.post(reverse("create_lesson", args=[self.course.id]), {
            "title": "Lesson A",
            "description": "Some desc",
            "objective": "Learn X",
            "effort_per_week": 2,
            "assignment": "Do something",
            "status": "PUBLISHED",
            "lesson_point": 5,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Lesson.objects.filter(title="Lesson A").exists())

    def test_instructor_can_delete_lesson(self):
        lesson = Lesson.objects.create(course=self.course, title="Lesson B", description="desc", designer=self.instructor)
        self.client.login(email="inst2@test.com", password="pass123")
        response = self.client.get(reverse("delete_lesson", args=[lesson.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lesson.objects.filter(title="Lesson B").exists())


# ------------------------------
# DEVELOPER STORIES
# ------------------------------
class DeveloperSetupTests(TestCase):
    def test_models_exist(self):
        # Ensure Course, Lesson, Enrolment models exist
        self.assertTrue(hasattr(Course, "_meta"))
        self.assertTrue(hasattr(Lesson, "_meta"))
        self.assertTrue(hasattr(Enrolment, "_meta"))

    def test_postgres_ready(self):
        # Create a dummy instructor because Course requires it
        instructor = User.objects.create_user(email="dummy@test.com", password="pass123", role="INSTRUCTOR")
        Course.objects.create(course_id="DEV001", title="Check DB", instructor=instructor)
        self.assertEqual(Course.objects.count(), 1)
