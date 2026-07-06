"""
Panther Assessment
Created by Darby Proctor, PhD. with assistance from Claude AI
Canvas Multi-Section Data Exporter - Main Application Window
PyQt6 GUI with university branding

Inspired by Doug Sandy's Canvascore
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QGroupBox, QMessageBox,
    QApplication, QLineEdit, QComboBox, QCheckBox, QDialog, QTabWidget,
    QMenu, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QIcon
import sys
from pathlib import Path

from src.utils.config import get_config
from src.api.canvas_client import SimpleBrowserAuthDialog, TokenBasedCanvasClient
from src.ui.dialogs.template_dialog import TemplateDialogMixin
from src.ui.dialogs.outcome_dialog import OutcomeDialogMixin
from src.ui.dialogs.report_dialog import ReportDialogMixin
import keyring
import requests

def _read_version() -> str:
    """Read version from VERSION file at repo root"""
    try:
        version_file = Path(__file__).parent.parent.parent / "VERSION"
        return version_file.read_text().strip()
    except Exception:
        return "unknown"

__version__ = _read_version()

def check_for_updates():
    try:
        response = requests.get(
            "https://api.github.com/repos/DarbyP/PantherAssessment/releases/latest",
            timeout=5
        )
        if response.status_code == 200:
            latest = response.json()["tag_name"].lstrip("v")
            if latest != __version__:
                return latest, response.json()["html_url"]
    except:
        pass
    return None, None

class MainWindow(TemplateDialogMixin, OutcomeDialogMixin, ReportDialogMixin, QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.canvas_client = None
        self.admin_mode = False
        
        self.setWindowTitle(f"Panther Assessment v{__version__}")
        self.setMinimumSize(1000, 700)  # Minimum size that fits on smaller screens
        self.resize(1000, 900)  # Default size, but resizable
        
        # Set window icon
        icon_path = Path(__file__).parent.parent.parent / 'assets' / 'panther.ico'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Create menu bar
        self.create_menu_bar()
        
        # Authenticate first
        if not self.authenticate():
            sys.exit(0)
        
        self.setup_ui()
        self.apply_styles()
        QApplication.styleHints().colorSchemeChanged.connect(self.apply_styles)
        self.check_template_migration()
        
        # Auto-load courses after UI is ready
        if self.canvas_client:
            self.search_courses()
        
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, self.check_updates)

    def check_updates(self):
        new_version, url = check_for_updates()
        if new_version:
            msg = QMessageBox(self)
            msg.setWindowTitle("Update Available")
            msg.setText(f"Version {new_version} is available.")
            msg.setInformativeText(f'<a href="{url}">Download here</a>')
            msg.setTextFormat(Qt.TextFormat.RichText)
            msg.exec()

    def authenticate(self) -> bool:
        """Authenticate with Canvas using API token"""
        # Check for saved Canvas URL
        try:
            canvas_url = keyring.get_password("PantherAssessment", "canvas_url")
        except:
            canvas_url = None
        
        # If no saved URL, prompt for it
        if not canvas_url:
            canvas_url = self.prompt_for_canvas_url()
            if not canvas_url:
                return False
            # Save the URL
            try:
                keyring.set_password("PantherAssessment", "canvas_url", canvas_url)
            except:
                pass
        
        # Try to get saved token from keyring
        try:
            saved_token = keyring.get_password("PantherAssessment", "canvas_token")
        except:
            saved_token = None
        
        if saved_token:
            # Test saved token
            client = TokenBasedCanvasClient(canvas_url, saved_token)
            if client.test_connection():
                self.canvas_client = client
                return True
            else:
                # Token invalid, delete it
                try:
                    keyring.delete_password("PantherAssessment", "canvas_token")
                except:
                    pass
        
        # Show token setup dialog
        auth_dialog = SimpleBrowserAuthDialog(canvas_url, self)
        
        if auth_dialog.exec() == QDialog.DialogCode.Accepted:
            token = auth_dialog.get_token()
            if token:
                # Create client and test
                client = TokenBasedCanvasClient(canvas_url, token)
                if client.test_connection():
                    # Save token securely
                    try:
                        keyring.set_password("PantherAssessment", "canvas_token", token)
                    except:
                        pass  # Continue even if keyring fails
                    
                    self.canvas_client = client
                    return True
                else:
                    # Ask if they want to change URL or try again
                    result = QMessageBox.critical(
                        self,
                        "Authentication Failed",
                        "Could not connect to Canvas. This could be due to:\n"
                        "• Invalid API token\n"
                        "• Incorrect Canvas URL\n\n"
                        "Would you like to change the Canvas URL?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if result == QMessageBox.StandardButton.Yes:
                        # Delete saved URL and try again
                        try:
                            keyring.delete_password("PantherAssessment", "canvas_url")
                        except:
                            pass
                        return self.authenticate()  # Start over with new URL
        
        return False
    
    def prompt_for_canvas_url(self) -> str:
        """Prompt user to enter their Canvas URL"""
        from PyQt6.QtWidgets import QInputDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Canvas URL Setup")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        instructions = QLabel(
            "Welcome to Panther Assessment!\n\n"
            "Please enter your institution's Canvas URL.\n"
            "Example: https://fit.instructure.com"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Canvas URL:"))
        url_input = QLineEdit()
        url_input.setPlaceholderText("https://")
        url_layout.addWidget(url_input)
        layout.addLayout(url_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Continue")
        cancel_btn = QPushButton("Cancel")
        
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn.setDefault(True)  # Make Continue the default button
        
        # Connect Enter key to submit
        url_input.returnPressed.connect(dialog.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            url = url_input.text().strip()
            # Validate URL format
            if url and (url.startswith('http://') or url.startswith('https://')):
                return url.rstrip('/')
            else:
                QMessageBox.warning(
                    self,
                    "Invalid URL",
                    "Please enter a valid URL starting with http:// or https://"
                )
                return self.prompt_for_canvas_url()  # Try again
        
        return ""
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # Settings / Help menu
        help_menu = menubar.addMenu("User Guide and Settings")

        guide_action = help_menu.addAction("Open User Guide")
        guide_action.triggered.connect(self.open_help_file)

        help_menu.addSeparator()

        url_action = help_menu.addAction("Change Canvas URL...")
        url_action.triggered.connect(self.change_canvas_url)
    
    def open_help_file(self):
        """Open the user guide document"""
        import subprocess
        import platform
        import sys
        import shutil
        import tempfile
        
        # Determine help file location in bundle
        if hasattr(sys, '_MEIPASS'):
            # Running as bundled app
            bundled_help = Path(sys._MEIPASS) / 'assets' / 'PantherAssessment_User_Guide.docx'
        else:
            # Running as script
            bundled_help = Path(__file__).parent.parent.parent / 'assets' / 'PantherAssessment_User_Guide.docx'
        
        if not bundled_help.exists():
            QMessageBox.warning(
                self,
                "Help File Not Found",
                f"User guide document could not be found.\nLooking for: {bundled_help}"
            )
            return
        
        try:
            # Copy to temp directory (files inside .app can't be opened directly)
            temp_dir = Path(tempfile.gettempdir()) / 'PantherAssessment'
            temp_dir.mkdir(exist_ok=True)
            temp_help = temp_dir / 'PantherAssessment_User_Guide.docx'
            shutil.copy(bundled_help, temp_help)
            
            # Open with system default application
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(temp_help)])
            elif platform.system() == 'Windows':
                subprocess.run(['start', '', str(temp_help)], shell=True)
            else:  # Linux
                subprocess.run(['xdg-open', str(temp_help)])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Opening File",
                f"Could not open user guide: {str(e)}"
            )
    
    def change_canvas_url(self):
        """Allow user to change Canvas URL"""
        result = QMessageBox.question(
            self,
            "Change Canvas URL",
            "This will reset your Canvas URL and require re-authentication.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            # Delete saved URL and token
            try:
                keyring.delete_password("PantherAssessment", "canvas_url")
                keyring.delete_password("PantherAssessment", "canvas_token")
            except:
                pass
            
            # Prompt for new URL and authenticate
            if self.authenticate():
                QMessageBox.information(
                    self,
                    "Success",
                    "Canvas URL updated successfully. Reloading courses..."
                )
                self.search_courses()
            else:
                QMessageBox.critical(
                    self,
                    "Setup Cancelled",
                    "Canvas URL was not changed."
                )
    
    def setup_ui(self):
        """Setup main window UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Course selection section
        course_section = self.create_course_selection()
        main_layout.addWidget(course_section)
        
        # Selected sections info
        self.selection_info = QLabel("No sections selected")
        self.selection_info.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        main_layout.addWidget(self.selection_info)
        
        # Template suggestion
        self.template_suggestion = QLabel("")
        self.template_suggestion.setVisible(False)
        main_layout.addWidget(self.template_suggestion)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        help_btn = QPushButton("User Guide")
        help_btn.clicked.connect(self.open_help_file)
        
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.close)
        
        button_layout.addWidget(help_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        # Developer credit at bottom
        credit_label = QLabel("Developed by: Darby Proctor, Ph.D. at Florida Tech")
        from src.utils.theme import get_palette, is_dark_mode
        _p = get_palette(self.config.primary_color, self.config.secondary_color, is_dark_mode())
        credit_label.setStyleSheet(f"color: {_p['text_disabled']}; font-size: 12px;")
        credit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(credit_label)
    
    def create_header(self) -> QWidget:
        """Create application header"""
        header = QWidget()
        layout = QHBoxLayout(header)
        
        # Panther Assessment logo on the left
        logo_label = QLabel()
        logo_path = Path(__file__).parent.parent.parent / 'assets' / 'panther_icon.png'
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            # Scale logo to reasonable size (height 80px)
            scaled_pixmap = pixmap.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        layout.addWidget(logo_label)
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Title and subtitle in center
        text_layout = QVBoxLayout()
        
        title = QLabel("Panther Assessment")
        title.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        subtitle = QLabel("Canvas Assessment Data Exporter")
        subtitle.setFont(QFont("Arial", 14))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        
        layout.addLayout(text_layout)
        layout.addStretch()  # Push everything to the left
        
        return header
    
    def create_course_selection(self) -> QGroupBox:
        """Create course selection section"""
        group = QGroupBox("Course Selection")
        layout = QVBoxLayout()
        
        # Filters group box — two rows
        filters_group = QGroupBox("Filters")
        filters_vlayout = QVBoxLayout()

        # Row 1: Course Code, Year, Semester, Search
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Course:"))
        self.course_code_filter = QLineEdit()
        self.course_code_filter.setPlaceholderText("PSY1411, 1411")
        self.course_code_filter.setMinimumWidth(150)
        self.course_code_filter.returnPressed.connect(self.search_courses)
        filter_layout.addWidget(self.course_code_filter)

        filter_layout.addSpacing(20)

        filter_layout.addWidget(QLabel("Year:"))
        self.year_filter = QComboBox()
        self.year_filter.addItem("")
        from datetime import datetime
        current_year = datetime.now().year
        for year in range(current_year - 3, current_year + 2):
            self.year_filter.addItem(str(year))
        filter_layout.addWidget(self.year_filter)

        filter_layout.addWidget(QLabel("Semester:"))
        self.semester_filter = QComboBox()
        self.semester_filter.addItems(["", "Fall", "Spring", "Summer"])
        filter_layout.addWidget(self.semester_filter)

        filter_layout.addWidget(QLabel("Term:"))
        self.term_filter = QComboBox()
        self.term_filter.addItems(["", "8-Week Term 1", "8-Week Term 2"])
        filter_layout.addWidget(self.term_filter)

        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self.search_courses)
        filter_layout.addWidget(search_btn)
        filter_layout.addStretch()
        filters_vlayout.addLayout(filter_layout)

        filters_group.setLayout(filters_vlayout)
        layout.addWidget(filters_group)

        # ── Admin only row ──────────────────────────────────────────────
        admin_group = QGroupBox("Admin Only")
        admin_layout = QHBoxLayout()

        self.admin_checkbox = QCheckBox("Enable Admin Mode")
        self.admin_checkbox.setToolTip("Show all courses you have admin access to")
        self.admin_checkbox.stateChanged.connect(self.toggle_admin_mode)
        admin_layout.addWidget(self.admin_checkbox)

        admin_layout.addSpacing(20)
        admin_layout.addWidget(QLabel("Account:"))
        self.account_filter = QComboBox()
        self.account_filter.addItem("All Accounts", None)
        self.account_filter.setEnabled(False)
        self.account_filter.setMinimumWidth(200)
        admin_layout.addWidget(self.account_filter)

        admin_layout.addStretch()
        admin_group.setLayout(admin_layout)
        layout.addWidget(admin_group)

        # Course list
        self.course_list = QListWidget()
        self.course_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        layout.addWidget(self.course_list)
                
        # Continue button
        continue_btn = QPushButton("Continue with Selected Sections")
        continue_btn.clicked.connect(self.load_assignments)
        layout.addWidget(continue_btn)
        
        group.setLayout(layout)
        return group
    
    def toggle_admin_mode(self, state):
        """Toggle admin mode — load accounts and enable admin filters"""
        self.admin_mode = bool(state)

        if self.admin_mode:
            if not self.canvas_client:
                self.admin_checkbox.setChecked(False)
                return

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                accounts = self.canvas_client.get_accounts()
            except Exception:
                accounts = []
            QApplication.restoreOverrideCursor()

            if not accounts:
                self.admin_checkbox.setChecked(False)
                self.admin_mode = False
                QMessageBox.warning(
                    self,
                    "No Admin Access",
                    "No admin accounts found.\nYou may not have admin access to any Canvas accounts."
                )
                return

            self.account_filter.clear()
            self.account_filter.addItem("All Accounts", None)
            for acc in accounts:
                self.account_filter.addItem(acc.get('name', 'Unknown'), acc.get('id'))
            self.account_filter.setEnabled(True)
            self.course_list.clear()
            self.selection_info.setText("Enter filters and click Search")
        else:
            self.account_filter.setEnabled(False)
            self.account_filter.clear()
            self.account_filter.addItem("All Accounts", None)

    def apply_styles(self):
        """Apply theme — automatically follows OS light/dark mode"""
        from src.utils.theme import apply_theme, is_dark_mode
        self.setStyleSheet(apply_theme(
            primary=self.config.primary_color,
            secondary=self.config.secondary_color,
            dark_mode=is_dark_mode()
        ))
    
    def search_courses(self):
        # Clear loaded template cache and outcome state — new course selection starts fresh
        self._loaded_template_filepath = None
        self._loaded_template_name = None
        if hasattr(self, 'outcome_list') and self.outcome_list:
            self.outcome_list.clear()
        if hasattr(self, 'outcome_parts_configs'):
            self.outcome_parts_configs = {}
        if hasattr(self, 'all_assignments'):
            self.all_assignments = []
        if hasattr(self, 'course_info'):
            self.course_info = []

        """Search for courses based on filters"""
        if not self.canvas_client:
            QMessageBox.warning(self, "Not Connected", "Please log in first.")
            return
        
        # Show loading message
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            # In admin mode, require at least one filter
            if self.admin_mode:
                course_code = self.course_code_filter.text().strip()
                year = self.year_filter.currentText().strip()
                semester = self.semester_filter.currentText().strip()
                term = self.term_filter.currentText().strip()

                if not course_code and not year and not semester and not term:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.information(
                        self,
                        "Filter Required",
                        "Admin mode has access to thousands of courses.\n\n"
                        "Please enter a course code, year, semester, or term to narrow results."
                    )
                    return

            # Fetch courses — in admin mode use selected account if specified
            selected_account_id = self.account_filter.currentData() if self.admin_mode else None
            courses = self.canvas_client.get_courses(
                admin_mode=self.admin_mode,
                account_id=selected_account_id
            )
            
            if not courses:
                if self.admin_mode:
                    msg = "No courses found. Your account may not have admin access to any courses."
                else:
                    msg = "No courses found. Make sure you're enrolled as a teacher."
                QApplication.restoreOverrideCursor()
                QMessageBox.information(self, "No Courses Found", msg)
                return
            
            # Get filter values
            course_code_filter = self.course_code_filter.text().strip().upper()
            year_filter = self.year_filter.currentText().strip()
            semester_filter = self.semester_filter.currentText().strip()
            term_filter = self.term_filter.currentText().strip()
            
            # Filter courses
            filtered_courses = []
            for course in courses:
                # Get course info
                course_name = course.get('name', '')
                course_code = course.get('course_code', '')
                term = course.get('term', {})
                term_name = term.get('name', '') if isinstance(term, dict) else ''

                # Exclude unpublished and zero-student courses
                if course.get('workflow_state') == 'unpublished':
                    continue
                if course.get('total_students', 1) == 0:
                    continue

                # Apply filters
                if course_code_filter and course_code_filter not in course_code.upper():
                    continue

                if year_filter and year_filter not in term_name:
                    continue

                if semester_filter and semester_filter not in term_name:
                    continue

                if term_filter and term_filter not in term_name:
                    continue

                filtered_courses.append(course)
            
            # Sort: alphabetically by course prefix, then most recent sections first
            import re as _re

            def course_sort_key(course):
                name = course.get('name', '')
                # Split at first comma to get prefix and section info
                parts = name.split(',', 1)
                prefix = parts[0].strip().upper()
                suffix = parts[1] if len(parts) > 1 else ''

                # Extract year (4-digit number)
                year_match = _re.search(r'(\d{4})', suffix)
                year = int(year_match.group(1)) if year_match else 0

                # Semester order within a year: Summer > Spring > Fall (most recent first)
                sem_order = 0
                suffix_upper = suffix.upper()
                if 'SUMMER' in suffix_upper:
                    sem_order = 3
                elif 'SPRING' in suffix_upper:
                    sem_order = 2
                elif 'FALL' in suffix_upper:
                    sem_order = 1

                # Sort: prefix ascending, then year descending, then semester descending
                return (prefix, -year, -sem_order)

            filtered_courses.sort(key=course_sort_key)

            # Update course list
            self.course_list.clear()
            for course in filtered_courses:
                course_name = course.get('name', 'Unnamed Course')
                teachers = course.get('teachers', [])
                if teachers:
                    teacher_names = ', '.join(t.get('display_name', '') for t in teachers if t.get('display_name'))
                    display_text = f"{course_name} — {teacher_names}"
                else:
                    display_text = course_name

                from PyQt6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, course)
                self.course_list.addItem(item)
            
            QApplication.restoreOverrideCursor()
            
            if not filtered_courses:
                QMessageBox.information(
                    self,
                    "No Matches",
                    "No courses match your search criteria."
                )
            else:
                self.selection_info.setText(f"Found {len(filtered_courses)} course(s)")
                
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Error",
                f"Error fetching courses:\n{str(e)}"
            )
    
    def load_assignments(self):
        """Load assignments from selected courses"""
        selected_items = self.course_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one course section."
            )
            return
        
        # Clear any previous outcome data to prevent stale state
        if hasattr(self, 'outcome_list'):
            self.outcome_list.clear()
        if hasattr(self, 'outcome_parts_configs'):
            self.outcome_parts_configs = {}
        
        # Show loading
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            # Get all assignments from selected courses
            all_assignments = []
            course_info = []
            
            # Track assignments by name to merge duplicates
            assignments_by_name = {}  # {assignment_name: assignment_data}
            
            for item in selected_items:
                course = item.data(Qt.ItemDataRole.UserRole)
                course_id = course.get('id')
                course_name = course.get('name', 'Unknown')
                
                assignments = self.canvas_client.get_assignments(course_id)
                
                for assignment in assignments:
                    assignment_name = assignment.get('name', 'Unnamed')
                    assignment_id = assignment.get('id')
                    quiz_id = assignment.get('quiz_id')
                    
                    # Extract short label: everything after first comma
                    parts = course_name.split(',', 1)
                    short_label = parts[1].strip() if len(parts) > 1 else course_name

                    if assignment_name in assignments_by_name:
                        existing = assignments_by_name[assignment_name]
                        if 'course_ids' not in existing:
                            existing['course_ids'] = [existing['course_id']]
                            existing['assignment_ids_by_course'] = {existing['course_id']: existing['id']}
                            existing['quiz_ids_by_course'] = {existing['course_id']: existing.get('quiz_id')}
                            existing['_course_names_by_id'] = {existing['course_id']: existing.get('_short_label', existing.get('_course_name', ''))}
                        existing['course_ids'].append(course_id)
                        existing['assignment_ids_by_course'][course_id] = assignment_id
                        existing['quiz_ids_by_course'][course_id] = quiz_id
                        existing['_course_names_by_id'][course_id] = short_label
                    else:
                        assignment['_course_name'] = course_name
                        assignment['_short_label'] = short_label
                        assignment['_course_names_by_id'] = {course_id: short_label}
                        assignment['course_id'] = course_id
                        assignment['course_ids'] = [course_id]
                        assignment['assignment_ids_by_course'] = {course_id: assignment_id}
                        assignment['quiz_ids_by_course'] = {course_id: quiz_id}
                        assignments_by_name[assignment_name] = assignment
                
                course_info.append({
                    'id': course_id,
                    'name': course_name,
                    'code': course.get('course_code', '')
                })
            
            # Convert dict to list, sorted alphabetically by assignment name
            all_assignments = sorted(assignments_by_name.values(), key=lambda a: a.get('name', '').strip().lower())
            
            QApplication.restoreOverrideCursor()
            
            if not all_assignments:
                QMessageBox.information(
                    self,
                    "No Assignments",
                    "No assignments found in selected courses."
                )
                return
            
            # Store assignments and go directly to outcome creation
            self.all_assignments = all_assignments
            self.course_info = course_info
            self.show_outcome_manager()
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Error",
                f"Error loading assignments:\n{str(e)}"
            )
    
def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application-wide font with larger size
    font = QFont("Arial", 16)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()