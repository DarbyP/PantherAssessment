"""
Canvas Authentication using System Browser
Opens default browser for login, captures session via local callback
"""

import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, 
    QLineEdit, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont



class CallbackHandler(BaseHTTPRequestHandler):
    """Handles OAuth callback from Canvas"""
    
    auth_data = None
    
    def do_GET(self):
        """Handle GET request with auth token"""
        query = parse_qs(urlparse(self.path).query)
        
        # Canvas returns code parameter
        if 'code' in query:
            CallbackHandler.auth_data = {
                'code': query['code'][0]
            }
            
            # Send success page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            success_html = """
            <html>
            <head><title>Login Successful</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>✓ Login Successful!</h1>
                <p>You can close this window and return to Panther Assessment.</p>
                <script>setTimeout(function(){ window.close(); }, 2000);</script>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
        else:
            # Error page
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_html = """
            <html>
            <head><title>Login Failed</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>Login Failed</h1>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
    
    def log_message(self, format, *args):
        """Suppress log messages"""
        pass


class BrowserAuthDialog(QDialog):
    """
    Dialog that opens system browser for Canvas login
    Waits for callback from Canvas OAuth
    """
    
    def __init__(self, canvas_url: str, parent=None):
        super().__init__(parent)
        self.canvas_url = canvas_url.rstrip('/')
        self.auth_code = None
        self.server = None
        self.server_thread = None
        
        self.setWindowTitle("Canvas Login")
        self.setFixedSize(500, 250)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Login to Canvas")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Your browser will open for Canvas login.\n\n"
            "After logging in, you'll be redirected back\n"
            "to this application automatically."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Status label
        self.status_label = QLabel("Waiting for login...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        # Start auth process
        QTimer.singleShot(500, self.start_auth)
    
    def start_auth(self):
        """Start local server and open browser"""
        # Start local callback server
        try:
            self.server = HTTPServer(('localhost', 8888), CallbackHandler)
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()
            
            # Open browser with Canvas login
            # Note: This uses manual redirect since Canvas OAuth requires app registration
            # For now, we'll use the simpler cookie-based approach with manual capture
            login_url = f"{self.canvas_url}/login"
            webbrowser.open(login_url)
            
            # Check for auth completion
            self.check_auth_timer = QTimer()
            self.check_auth_timer.timeout.connect(self.check_auth_complete)
            self.check_auth_timer.start(500)  # Check every 500ms
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
    
    def run_server(self):
        """Run callback server"""
        try:
            self.server.serve_forever()
        except:
            pass
    
    def check_auth_complete(self):
        """Check if authentication completed"""
        if CallbackHandler.auth_data:
            self.auth_code = CallbackHandler.auth_data.get('code')
            self.check_auth_timer.stop()
            self.cleanup_server()
            self.accept()
    
    def cleanup_server(self):
        """Stop callback server"""
        if self.server:
            self.server.shutdown()
    
    def closeEvent(self, event):
        """Clean up on close"""
        self.cleanup_server()
        super().closeEvent(event)
    
    def get_auth_code(self):
        """Get authorization code"""
        return self.auth_code


class SimpleBrowserAuthDialog(QDialog):
    """
    Simplified browser auth - just instructs user to get API token manually
    Most reliable method for Canvas
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
        
        # Title
        title = QLabel("First Time Setup")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Instructions
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
        
        # Open button
        open_btn = QPushButton("Open Canvas Settings")
        open_btn.clicked.connect(self.open_canvas_settings)
        layout.addWidget(open_btn)
        
        # Token input
        token_label = QLabel("Paste your API token:")
        layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste token here...")
        self.token_input.returnPressed.connect(self.save_token)  # Connect Enter key to submit
        layout.addWidget(self.token_input)
        
        # Buttons
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
            QMessageBox.warning(
                self,
                "No Token",
                "Please enter your API token."
            )
    
    def get_token(self):
        """Get API token"""
        return self.api_token


class TokenBasedCanvasClient:
    """
    Canvas API client using API token
    Simple and reliable method
    """
    
    def __init__(self, base_url: str, api_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = None
        
        if api_token:
            self.set_token(api_token)
    
    def set_token(self, api_token: str):
        """Set API token"""
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
        except:
            return False
    
    def get_user_info(self) -> dict:
        """Get current user information"""
        if not self.session:
            return {}
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/users/self", timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
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
        except:
            pass
        return []

    def get_courses(self, enrollment_type: str = 'teacher', admin_mode: bool = False) -> list:
        """Get user's courses"""
        if not self.session:
            return []
        
        try:
            if admin_mode:
                # Get all courses from accounts user has admin access to
                accounts = self.get_accounts()
                all_courses = []
                for account in accounts:
                    account_id = account.get('id')
                    if account_id:
                        # Paginate through all courses
                        url = f"{self.base_url}/api/v1/accounts/{account_id}/courses"
                        params = {
                            'include[]': ['term', 'total_students'],
                            'per_page': 100,
                            'with_enrollments': 'true',
                            'state[]': ['available', 'completed']
                        }
                        while url:
                            response = self.session.get(url, params=params, timeout=30)
                            if response.status_code == 200:
                                all_courses.extend(response.json())
                                # Check for next page
                                url = None
                                params = None  # URL includes params after first request
                                links = response.headers.get('Link', '')
                                for link in links.split(','):
                                    if 'rel="next"' in link:
                                        url = link.split(';')[0].strip('<> ')
                                        break
                            else:
                                break
                return all_courses
            else:
                # Standard instructor mode with pagination
                url = f"{self.base_url}/api/v1/courses"
                params = {
                    'enrollment_type': enrollment_type,
                    'enrollment_state': 'active',
                    'include[]': ['term', 'total_students'],
                    'per_page': 100
                }
                all_courses = []
                while url:
                    response = self.session.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        all_courses.extend(response.json())
                        # Check for next page
                        url = None
                        params = None  # URL includes params after first request
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
    
    def get_assignments(self, course_id: int) -> list:
        """Get assignments for a course"""
        if not self.session:
            return []
        
        try:
            params = {
                'per_page': 100,
                'include[]': ['rubric']
            }
            
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/assignments",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        
        return []
    
    def get_assignment(self, course_id: int, assignment_id: int) -> dict:
        """Get details for a specific assignment"""
        if not self.session:
            return {}
        
        try:
            params = {
                'include[]': ['rubric']
            }
            
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}",
                params=params,
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
            params = {
                'type[]': 'StudentEnrollment',
                'state[]': 'active',
                'per_page': 100
            }
            
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/enrollments",
                params=params,
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
            params = {
                'per_page': 100,
                'include[]': ['user', 'rubric_assessment']
            }
            
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions",
                params=params,
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
        """Get quiz submissions with question-level details"""
        if not self.session:
            return []
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions",
                params={'per_page': 100},
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