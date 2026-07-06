"""
Canvas Authentication and API Client
"""

import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SimpleBrowserAuthDialog(QDialog):
    """
    Dialog that instructs user to create a Canvas API token manually.
    Most reliable method for Canvas authentication.
    """

    def __init__(self, canvas_url: str, parent=None):
        super().__init__(parent)
        self.canvas_url = canvas_url.rstrip('/')
        self.api_token = None

        self.setWindowTitle("Canvas API Token Setup")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("First Time Setup")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        instructions = QLabel(
            "<b>First-time setup: Create a Canvas API token that will automatically log you in to Canvas</b><br><br>"
            "<b>Step 1:</b> Click 'Open Canvas Settings' below<br>"
            "<b>Step 2:</b> In Canvas, scroll down to <b>Approved Integrations</b><br>"
            "<b>Step 3:</b> Click <b>+ New Access Token</b><br>"
            "<b>Step 4:</b> Purpose: <b>Panther Assessment</b><br>"
            "<b>Step 5:</b> Leave expiration blank (never expires)<br>"
            "<b>Step 6:</b> Click <b>Generate Token</b><br>"
            "<b>Step 7:</b> Copy the token and paste below<br><br>"
            "<i>Note: You only need to do this once. Your token will be saved securely.</i>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        open_btn = QPushButton("Open Canvas Settings")
        open_btn.clicked.connect(self.open_canvas_settings)
        layout.addWidget(open_btn)

        token_label = QLabel("Paste your API token:")
        layout.addWidget(token_label)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste token here...")
        self.token_input.returnPressed.connect(self.save_token)
        layout.addWidget(self.token_input)

        button_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Save Token")
        ok_btn.clicked.connect(self.save_token)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

    def open_canvas_settings(self):
        """Open Canvas settings page in browser"""
        settings_url = f"{self.canvas_url}/profile/settings"
        webbrowser.open(settings_url)

    def save_token(self):
        """Save API token"""
        token = self.token_input.text().strip()
        if token:
            self.api_token = token
            self.accept()
        else:
            QMessageBox.warning(self, "No Token", "Please enter your API token.")

    def get_token(self):
        """Get API token"""
        return self.api_token


class TokenBasedCanvasClient:
    """
    Canvas API client using API token authentication.
    """

    def __init__(self, base_url: str, api_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = None

        if api_token:
            self.set_token(api_token)

    def set_token(self, api_token: str):
        """Set API token and configure session"""
        import requests
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def test_connection(self) -> bool:
        """Test Canvas API connection"""
        if not self.session:
            return False
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/users/self",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_user_info(self) -> dict:
        """Get current user information"""
        if not self.session:
            return {}
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/users/self",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {}

    def get_accounts(self) -> list:
        """Get accounts user has admin access to"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/accounts",
                params={'per_page': 100},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def get_courses(self, enrollment_type: str = 'teacher', admin_mode: bool = False, account_id=None) -> list:
        """Get user's courses with pagination"""
        if not self.session:
            return []
        try:
            if admin_mode:
                if account_id:
                    accounts = [{'id': account_id}]
                else:
                    accounts = self.get_accounts()
                all_courses = []
                for account in accounts:
                    acct_id = account.get('id')
                    if acct_id:
                        url = f"{self.base_url}/api/v1/accounts/{acct_id}/courses"
                        params = [
                            ('include[]', 'term'),
                            ('include[]', 'total_students'),
                            ('include[]', 'teachers'),
                            ('per_page', 100),
                            ('with_enrollments', 'true'),
                            ('state[]', 'available'),
                            ('state[]', 'completed'),
                        ]
                        while url:
                            response = self.session.get(url, params=params, timeout=30)
                            if response.status_code == 200:
                                all_courses.extend(response.json())
                                url = None
                                links = response.headers.get('Link', '')
                                for link in links.split(','):
                                    if 'rel="next"' in link:
                                        url = link.split(';')[0].strip('<> ')
                                        break
                            else:
                                break
                return all_courses
            else:
                url = f"{self.base_url}/api/v1/courses"
                params = {
                    'enrollment_type': enrollment_type,
                    'enrollment_state': 'active',
                    'include[]': ['term', 'total_students', 'teachers'],
                    'per_page': 100
                }
                all_courses = []
                while url:
                    response = self.session.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        all_courses.extend(response.json())
                        url = None
                        links = response.headers.get('Link', '')
                        for link in links.split(','):
                            if 'rel="next"' in link:
                                url = link.split(';')[0].strip('<> ')
                                break
                    else:
                        break
                return all_courses
        except Exception:
            pass
        return []

    def get_course_teachers(self, course_id: int) -> list:
        """Get teacher enrollments for a course"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/enrollments",
                params={'type[]': 'TeacherEnrollment', 'per_page': 100},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def get_assignments(self, course_id: int) -> list:
        """Get assignments for a course"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/assignments",
                params={'per_page': 100, 'include[]': ['rubric']},
                timeout=30
            )
            if response.status_code == 200:
                assignments = response.json()
                return [a for a in assignments if a.get('published', True)]
        except Exception:
            pass
        return []

    def get_assignment(self, course_id: int, assignment_id: int) -> dict:
        """Get details for a specific assignment"""
        if not self.session:
            return {}
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}",
                params={'include[]': ['rubric']},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {}

    def get_enrollments(self, course_id: int) -> list:
        """Get student enrollments for a course"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/enrollments",
                params={
                    'type[]': 'StudentEnrollment',
                    'state[]': 'active',
                    'per_page': 100,
                    'include[]': 'sis_user_id'
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def get_submissions(self, course_id: int, assignment_id: int) -> list:
        """Get submissions for an assignment"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions",
                params={'per_page': 100, 'include[]': ['user', 'rubric_assessment']},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def get_quiz_questions(self, course_id: int, quiz_id: int) -> list:
        """Get questions for a quiz"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions",
                params={'per_page': 100},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def get_quiz_groups(self, course_id: int, quiz_id: int) -> list:
        """Get question groups for a quiz"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}/groups",
                params={'per_page': 100},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def get_quiz_submissions(self, course_id: int, quiz_id: int) -> list:
        """Get quiz submissions"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions",
                params={'per_page': 100, 'include[]': 'submission'},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('quiz_submissions', [])
        except Exception:
            pass
        return []

    def get_quiz_submission_questions(self, quiz_submission_id: int) -> list:
        """Get questions and answers for a specific quiz submission"""
        if not self.session:
            return []
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/quiz_submissions/{quiz_submission_id}/questions",
                params={'per_page': 100},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    if 'quiz_submission_questions' in data:
                        return data['quiz_submission_questions']
                return data
        except Exception:
            pass
        return []
