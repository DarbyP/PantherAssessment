"""
Panther Assessment
Created by Darby Proctor, PhD. with assistance from Claude AI
Canvas Multi-Section Data Exporter - Main Application Window
PyQt6 GUI with university branding

Insipred by Doug Sandy's Canvasore
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
from src.api.browser_auth import SimpleBrowserAuthDialog, TokenBasedCanvasClient
import keyring


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.canvas_client = None
        
        self.setWindowTitle("Panther Assessment - Canvas Assessment Data Exporter")
        self.setMinimumSize(1000, 600)  # Minimum size that fits on smaller screens
        self.resize(1000, 650)  # Default size, works with 150% DPI scaling
        

        # Set window icon - try PNG first (higher quality), fallback to ICO
        icon_path = Path(__file__).parent.parent.parent / 'assets' / 'panther.png'
        if not icon_path.exists():
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
        
        # Auto-load courses after UI is ready
        if self.canvas_client:
            self.search_courses()
    
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
        """Create menu bar with User Guide menu"""
        menubar = self.menuBar()
        
        # User Guide menu
        help_menu = menubar.addMenu("User Guide and Settings")
        
        # Open User Guide action
        guide_action = help_menu.addAction("Open User Guide")
        guide_action.triggered.connect(self.open_help_file)
        
        help_menu.addSeparator()
        
        # Change Canvas URL action
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
        credit_label.setStyleSheet("color: #999999; font-size: 12px;")
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
        
        # Filters group box
        filters_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Course Code:"))
        self.course_code_filter = QLineEdit()
        self.course_code_filter.setPlaceholderText("e.g., PSY1411, 1411")
        self.course_code_filter.returnPressed.connect(self.search_courses)  # Enter key
        filter_layout.addWidget(self.course_code_filter)
        
        # Spacer before year/semester
        filter_layout.addSpacing(20)
        
        filter_layout.addWidget(QLabel("Year:"))
        self.year_filter = QComboBox()
        self.year_filter.addItem("")  # Blank option
        from datetime import datetime
        current_year = datetime.now().year
        for year in range(current_year - 3, current_year + 2):
            self.year_filter.addItem(str(year))
        # Dynamic filtering - instant for dropdowns
        self.year_filter.currentTextChanged.connect(self.search_courses)
        filter_layout.addWidget(self.year_filter)
        
        filter_layout.addWidget(QLabel("Semester:"))
        self.semester_filter = QComboBox()
        self.semester_filter.addItems(["", "Fall", "Spring", "Summer"])
        # Dynamic filtering - instant for dropdowns
        self.semester_filter.currentTextChanged.connect(self.search_courses)
        filter_layout.addWidget(self.semester_filter)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self.search_courses)
        filter_layout.addWidget(search_btn)
        
        filters_group.setLayout(filter_layout)
        layout.addWidget(filters_group)
        
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
    
    def apply_styles(self):
        """Apply university color scheme to entire application"""
        primary = self.config.primary_color
        secondary = self.config.secondary_color
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: white;
            }}
            QLabel {{
                color: #333333;
                font-size: 16px;
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: 17px;
                border: 2px solid {secondary};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                color: {primary};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QPushButton {{
                background-color: {primary};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: #5a0000;
            }}
            QPushButton:pressed {{
                background-color: #3d0000;
            }}
            QLineEdit {{
                padding: 8px;
                border: 2px solid {secondary};
                border-radius: 4px;
                font-size: 16px;
                min-height: 25px;
            }}
            QLineEdit:focus {{
                border-color: {primary};
            }}
            QListWidget {{
                border: 2px solid {secondary};
                border-radius: 4px;
                font-size: 16px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 2px;
            }}
            QListWidget::item:selected {{
                background-color: {primary};
                color: white;
            }}
            QCheckBox {{
                spacing: 10px;
                font-size: 16px;
            }}
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border: 2px solid {secondary};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {primary};
                border-color: {primary};
            }}
            QMenuBar {{
                background-color: white;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QMenuBar::item {{
                background-color: {primary};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                margin-right: 5px;
            }}
            QMenuBar::item:selected {{
                background-color: #5a0000;
            }}
            QMenuBar::item:pressed {{
                background-color: #3d0000;
            }}
            QMenu {{
                background-color: white;
                border: 2px solid {secondary};
                border-radius: 4px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 30px 8px 20px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {primary};
                color: white;
            }}
            QTabWidget::pane {{
                border: 2px solid {secondary};
                border-radius: 4px;
            }}
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background-color: #f0f0f0;
                color: #333333;
                border: 2px solid {secondary};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 10px 20px;
                margin-right: 2px;
                font-size: 16px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: white;
                color: {primary};
                border-color: {primary};
                border-bottom: 2px solid white;
            }}
            QTabBar::tab:hover {{
                background-color: #e8e8e8;
            }}
        """)
    
    def search_courses(self):
        """Search for courses based on filters"""
        if not self.canvas_client:
            QMessageBox.warning(self, "Not Connected", "Please log in first.")
            return
        
        # Show loading message
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            # Fetch courses from Canvas
            courses = self.canvas_client.get_courses()
            
            if not courses:
                QApplication.restoreOverrideCursor()
                QMessageBox.information(
                    self,
                    "No Courses Found",
                    "No courses found. Make sure you're enrolled as a teacher."
                )
                return
            
            # Get filter values
            course_code_filter = self.course_code_filter.text().strip().upper()
            year_filter = self.year_filter.currentText().strip()
            semester_filter = self.semester_filter.currentText().strip()
            
            # Filter courses
            filtered_courses = []
            for course in courses:
                # Get course info
                course_name = course.get('name', '')
                course_code = course.get('course_code', '')
                term = course.get('term', {})
                term_name = term.get('name', '') if isinstance(term, dict) else ''
                
                # Apply filters
                if course_code_filter and course_code_filter not in course_code.upper():
                    continue
                
                if year_filter and year_filter not in term_name:
                    continue
                
                if semester_filter and semester_filter not in term_name:
                    continue
                
                filtered_courses.append(course)
            
            # Update course list
            self.course_list.clear()
            for course in filtered_courses:
                course_name = course.get('name', 'Unnamed Course')
                term = course.get('term', {})
                term_name = term.get('name', 'No Term') if isinstance(term, dict) else 'No Term'
                
                display_text = f"{course_name} ({term_name})"
                
                from PyQt6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, course)  # Store course data
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
    
    def show_template_manager(self):
        """Show template manager dialog"""
        from PyQt6.QtWidgets import QFormLayout, QTextEdit, QSpinBox
        from pathlib import Path
        from src.models.template_models import TemplateManager
        from src.utils.resources import get_user_templates_dir
        
        # Initialize template manager with user templates directory
        template_dir = get_user_templates_dir()
        template_mgr = TemplateManager(template_dir)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Template Manager")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Template list
        layout.addWidget(QLabel("Saved Templates:"))
        template_list = QListWidget()
        template_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Load templates
        def refresh_templates():
            template_list.clear()
            templates = template_mgr.list_templates()
            for template in templates:
                item = QListWidgetItem(
                    f"{template.template_name} ({template.course_code}) - "
                    f"{len(template.outcomes)} outcomes - "
                    f"Modified: {template.last_modified.strftime('%Y-%m-%d')}"
                )
                item.setData(Qt.ItemDataRole.UserRole, template)
                template_list.addItem(item)
        
        refresh_templates()
        layout.addWidget(template_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        apply_btn = QPushButton("Apply Template")
        apply_btn.clicked.connect(lambda: self.apply_template(dialog, template_list))
        
        edit_btn = QPushButton("Edit Template")
        edit_btn.clicked.connect(lambda: self.edit_template(dialog, template_list, refresh_templates))
        
        delete_btn = QPushButton("Delete Template")
        delete_btn.clicked.connect(lambda: self.delete_template(template_list, template_mgr, refresh_templates))
        
        save_btn = QPushButton("Save Current as Template")
        save_btn.clicked.connect(lambda: self.save_as_template(template_mgr, refresh_templates))
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec()
    
    def apply_template(self, parent_dialog, template_list):
        """Apply selected template to current outcomes"""
        items = template_list.selectedItems()
        if not items:
            QMessageBox.warning(parent_dialog, "No Selection", "Select a template to apply.")
            return
        
        template = items[0].data(Qt.ItemDataRole.UserRole)
        
        # Confirm
        reply = QMessageBox.question(
            parent_dialog,
            "Apply Template",
            f"Apply template '{template.template_name}'?\n"
            f"This will replace current outcome configuration.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Clear current outcomes
        self.outcome_list.clear()
        if hasattr(self, 'outcome_parts_configs'):
            self.outcome_parts_configs = {}
        
        # Convert template outcomes to outcome list items
        for outcome in template.outcomes:
            if not outcome.included:
                continue
            
            # Find matching assignments in loaded assignments (by name only)
            selected_assignments = []
            parts_config = {}
            
            for template_assign in outcome.assignments:
                if not template_assign.included:
                    continue
                
                # Match assignment by name
                matched_assignment = None
                for assignment in self.all_assignments:
                    if assignment.get('name') == template_assign.name:
                        matched_assignment = assignment
                        break
                
                if matched_assignment:
                    selected_assignments.append(matched_assignment)
                    assignment_id = matched_assignment.get('id')
                    
                    # Re-discover parts from current courses
                    parts = []
                    
                    # Get all courses for this assignment
                    course_ids = matched_assignment.get('course_ids', [matched_assignment.get('course_id')])
                    quiz_ids_by_course = matched_assignment.get('quiz_ids_by_course', {})
                    
                    # Re-discover quiz groups by name
                    for template_qg in template_assign.question_groups:
                        if not template_qg.selected:
                            continue
                        
                        groups_by_name = {}
                        
                        for cid in course_ids:
                            qid = quiz_ids_by_course.get(cid) or matched_assignment.get('quiz_id')
                            if not qid:
                                continue
                            
                            try:
                                questions = self.canvas_client.get_quiz_questions(cid, qid)
                                group_ids = {q.get('quiz_group_id') for q in questions if q.get('quiz_group_id')}
                                
                                for group_id in group_ids:
                                    try:
                                        response = self.canvas_client.session.get(
                                            f"{self.canvas_client.base_url}/api/v1/courses/{cid}/quizzes/{qid}/groups/{group_id}",
                                            timeout=30
                                        )
                                        if response.status_code == 200:
                                            group = response.json()
                                            group_name = group.get('name')
                                            
                                            # Match by name
                                            if group_name == template_qg.name:
                                                if group_name not in groups_by_name:
                                                    groups_by_name[group_name] = {
                                                        'group_ids_by_course': {},
                                                        'pick_count_by_course': {},
                                                        'question_points_by_course': {}
                                                    }
                                                groups_by_name[group_name]['group_ids_by_course'][str(cid)] = str(group_id)
                                                groups_by_name[group_name]['pick_count_by_course'][str(cid)] = group.get('pick_count', 0)
                                                groups_by_name[group_name]['question_points_by_course'][str(cid)] = group.get('question_points', 0)
                                    except:
                                        pass
                            except:
                                pass
                        
                        # Add collected groups to parts
                        for group_name, group_data in groups_by_name.items():
                            parts.append({
                                'type': 'quiz_group',
                                'group_name': group_name,
                                'group_ids_by_course': group_data['group_ids_by_course'],
                                'pick_count_by_course': group_data['pick_count_by_course'],
                                'question_points_by_course': group_data['question_points_by_course'],
                                'assignment_id': assignment_id
                            })
                    
                    # Re-discover rubric criteria by description
                    for template_rc in template_assign.rubric_criteria:
                        if not template_rc.selected:
                            continue
                        
                        criteria_by_description = {}
                        
                        for cid in course_ids:
                            aid = matched_assignment.get('assignment_ids_by_course', {}).get(cid, matched_assignment.get('id'))
                            
                            try:
                                course_assignment = self.canvas_client.get_assignment(cid, aid)
                                course_rubric = course_assignment.get('rubric', [])
                                
                                for criterion in course_rubric:
                                    criterion_description = criterion.get('description', '').strip()
                                    criterion_id = criterion.get('id')
                                    
                                    # Match by description (case-insensitive, trimmed)
                                    if criterion_description.lower() == template_rc.description.lower().strip():
                                        if criterion_description not in criteria_by_description:
                                            criteria_by_description[criterion_description] = {
                                                'criterion_ids_by_course': {},
                                                'points': criterion.get('points', 0)
                                            }
                                        criteria_by_description[criterion_description]['criterion_ids_by_course'][str(cid)] = str(criterion_id)
                            except:
                                pass
                        
                        # Add collected criteria to parts
                        for description, criterion_data in criteria_by_description.items():
                            parts.append({
                                'type': 'rubric_criterion',
                                'description': description,
                                'criterion_ids_by_course': criterion_data['criterion_ids_by_course'],
                                'points': criterion_data['points'],
                                'assignment_id': assignment_id
                            })
                    
                    if parts:
                        parts_config[assignment_id] = parts
            
            if selected_assignments:
                # Add outcome to list
                outcome_text = f"{outcome.title} ({outcome.threshold}%) - {len(selected_assignments)} assignment(s)"
                item = QListWidgetItem(outcome_text)
                item.setData(Qt.ItemDataRole.UserRole, {
                    'name': outcome.title,
                    'description': outcome.description,
                    'threshold': outcome.threshold,
                    'assignments': selected_assignments,
                    'parts_config': parts_config
                })
                self.outcome_list.addItem(item)
                
                # Store parts config
                if not hasattr(self, 'outcome_parts_configs'):
                    self.outcome_parts_configs = {}
                self.outcome_parts_configs[outcome.title] = parts_config
        
        parent_dialog.accept()
        QMessageBox.information(
            self,
            "Template Applied",
            f"Loaded {self.outcome_list.count()} outcomes from template."
        )
    
    def edit_template(self, parent_dialog, template_list, refresh_callback):
        """Edit selected template"""
        items = template_list.selectedItems()
        if not items:
            QMessageBox.warning(parent_dialog, "No Selection", "Select a template to edit.")
            return
        
        template = items[0].data(Qt.ItemDataRole.UserRole)
        
        # Edit dialog
        from PyQt6.QtWidgets import QFormLayout, QTextEdit
        from pathlib import Path
        from src.models.template_models import TemplateManager
        
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle(f"Edit Template: {template.template_name}")
        dialog.setMinimumSize(600, 400)
        
        layout = QFormLayout(dialog)
        
        name_input = QLineEdit(template.template_name)
        layout.addRow("Template Name:", name_input)
        
        code_input = QLineEdit(template.course_code)
        layout.addRow("Course Code:", code_input)
        
        notes_input = QTextEdit(template.notes)
        notes_input.setMaximumHeight(100)
        layout.addRow("Notes:", notes_input)
        
        # Buttons
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        
        def save_changes():
            from src.utils.resources import get_user_templates_dir
            
            template.template_name = name_input.text().strip()
            template.course_code = code_input.text().strip()
            template.notes = notes_input.toPlainText()
            
            template_dir = get_user_templates_dir()
            template_mgr = TemplateManager(template_dir)
            template_mgr.save_template(template)
            
            dialog.accept()
            refresh_callback()
            QMessageBox.information(parent_dialog, "Saved", "Template updated.")
        
        buttons.accepted.connect(save_changes)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.exec()
    
    def delete_template(self, template_list, template_mgr, refresh_callback):
        """Delete selected template"""
        items = template_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "No Selection", "Select a template to delete.")
            return
        
        template = items[0].data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self,
            "Delete Template",
            f"Delete template '{template.template_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if template_mgr.delete_template(template.course_code, template.template_name):
                refresh_callback()
                QMessageBox.information(self, "Deleted", "Template deleted.")
            else:
                QMessageBox.warning(self, "Error", "Could not delete template.")
    
    def save_as_template(self, template_mgr, refresh_callback):
        """Save current outcome configuration as template"""
        if self.outcome_list.count() == 0:
            QMessageBox.warning(self, "No Outcomes", "Configure outcomes first.")
            return
        
        # Get template info
        from PyQt6.QtWidgets import QFormLayout, QTextEdit
        from datetime import datetime
        from src.models.template_models import CourseTemplate, TemplateOutcome, TemplateAssignment, TemplateQuestionGroup, TemplateRubricCriterion
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Save as Template")
        dialog.setMinimumWidth(500)
        
        layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g., Standard Assessment")
        layout.addRow("Template Name:", name_input)
        
        # Try to extract course code from first course
        course_code = "UNKNOWN"
        if hasattr(self, 'all_assignments') and self.all_assignments:
            first_course = self.all_assignments[0].get('_course_name', '')
            # Extract code (e.g., "PSY3421" from "PSY3421 - Intro to Psychology")
            parts = first_course.split()
            if parts:
                course_code = parts[0]
        
        code_input = QLineEdit(course_code)
        layout.addRow("Course Code:", code_input)
        
        notes_input = QTextEdit()
        notes_input.setMaximumHeight(100)
        notes_input.setPlaceholderText("Optional notes about this template...")
        layout.addRow("Notes:", notes_input)
        
        # Buttons
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        
        def save():
            name = name_input.text().strip()
            code = code_input.text().strip()
            
            if not name:
                QMessageBox.warning(dialog, "Missing Name", "Enter a template name.")
                return
            
            # Build template from current outcomes
            outcomes = []
            for i in range(self.outcome_list.count()):
                item = self.outcome_list.item(i)
                outcome_data = item.data(Qt.ItemDataRole.UserRole)
                
                assignments = []
                parts_config = outcome_data.get('parts_config', {})
                
                for assignment in outcome_data['assignments']:
                    assignment_id = assignment.get('id')
                    
                    # Get parts for this assignment
                    question_groups = []
                    rubric_criteria = []
                    
                    if assignment_id in parts_config:
                        for part in parts_config[assignment_id]:
                            if part.get('type') == 'quiz_group':
                                question_groups.append(TemplateQuestionGroup(
                                    name=part.get('group_name', 'Unknown'),
                                    selected=True
                                ))
                            elif part.get('type') == 'rubric_criterion':
                                rubric_criteria.append(TemplateRubricCriterion(
                                    description=part.get('description', 'Unknown'),
                                    selected=True
                                ))
                    
                    assignments.append(TemplateAssignment(
                        name=assignment.get('name', 'Unknown'),
                        assignment_type='quiz' if assignment.get('quiz_id') else 'assignment',
                        included=True,
                        question_groups=question_groups,
                        rubric_criteria=rubric_criteria
                    ))
                
                outcomes.append(TemplateOutcome(
                    title=outcome_data['name'],
                    description=outcome_data.get('description', ''),
                    threshold=outcome_data['threshold'],
                    included=True,
                    assignments=assignments
                ))
            
            template = CourseTemplate(
                template_name=name,
                course_code=code,
                created_date=datetime.now(),
                last_modified=datetime.now(),
                created_by="User",
                outcomes=outcomes,
                notes=notes_input.toPlainText()
            )
            
            template_mgr.save_template(template)
            dialog.accept()
            refresh_callback()
            QMessageBox.information(self, "Saved", f"Template '{name}' saved.")
        
        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.exec()
    
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
                    
                    if assignment_name in assignments_by_name:
                        # Assignment with this name already exists - merge course_ids, assignment_ids, and quiz_ids
                        existing = assignments_by_name[assignment_name]
                        if 'course_ids' not in existing:
                            # First time merging - convert single values to lists/dicts
                            existing['course_ids'] = [existing['course_id']]
                            existing['assignment_ids_by_course'] = {existing['course_id']: existing['id']}
                            existing['quiz_ids_by_course'] = {existing['course_id']: existing.get('quiz_id')}
                        existing['course_ids'].append(course_id)
                        existing['assignment_ids_by_course'][course_id] = assignment_id
                        existing['quiz_ids_by_course'][course_id] = quiz_id
                    else:
                        # New assignment - add it
                        assignment['_course_name'] = course_name
                        assignment['course_id'] = course_id
                        assignment['course_ids'] = [course_id]  # Start as list
                        assignment['assignment_ids_by_course'] = {course_id: assignment_id}  # Map course to assignment_id
                        assignment['quiz_ids_by_course'] = {course_id: quiz_id}  # Map course to quiz_id
                        assignments_by_name[assignment_name] = assignment
                
                course_info.append({
                    'id': course_id,
                    'name': course_name,
                    'code': course.get('course_code', '')
                })
            
            # Convert dict to list
            all_assignments = list(assignments_by_name.values())
            
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
    
    def show_outcome_manager(self):
        """Show dialog to manage outcomes"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Configure Assessment Outcomes")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        instructions = QLabel(
            f"Selected {len(self.course_info)} course section(s) with {len(self.all_assignments)} assignment(s).\n\n"
            "Create custom outcomes and assign assessments to each one."
        )
        layout.addWidget(instructions)
        
        # Outcomes list
        outcome_group = QGroupBox("Custom Outcomes")
        outcome_layout = QVBoxLayout()
        
        self.outcome_list = QListWidget()
        self.outcome_list.itemDoubleClicked.connect(self.edit_outcome)
        outcome_layout.addWidget(self.outcome_list)
        
        # Add outcome button
        add_outcome_btn = QPushButton("+ Add Outcome")
        add_outcome_btn.clicked.connect(self.add_outcome_dialog)
        outcome_layout.addWidget(add_outcome_btn)
        
        # Load template button
        load_template_btn = QPushButton("📁 Load Template")
        load_template_btn.clicked.connect(self.load_template_dialog)
        outcome_layout.addWidget(load_template_btn)
        
        outcome_group.setLayout(outcome_layout)
        layout.addWidget(outcome_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        generate_btn = QPushButton("Generate Report")
        generate_btn.clicked.connect(lambda: self.generate_report_from_outcomes(dialog))
        
        save_template_btn = QPushButton("Save as Template")
        save_template_btn.clicked.connect(lambda: self.save_template_dialog(dialog))
        
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_template_btn)
        button_layout.addWidget(generate_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.outcome_dialog = dialog
        dialog.exec()
    
    def save_template_dialog(self, parent_dialog):
        """Save current outcomes as a template"""
        from datetime import datetime
        
        if self.outcome_list.count() == 0:
            QMessageBox.warning(
                parent_dialog,
                "No Outcomes",
                "Please create at least one outcome before saving a template."
            )
            return
        
        # Extract course codes from selected courses
        course_codes = []
        if self.course_info:
            for course in self.course_info:
                course_name = course.get('name', '')
                # Try to extract course code (letters + numbers at start)
                import re
                match = re.match(r'^([A-Z]+\s*\d+)', course_name)
                if match:
                    course_code = match.group(1).replace(' ', '')
                    if course_code not in course_codes:
                        course_codes.append(course_code)
        
        # Build suggested suffix
        course_suffix = '_' + '_'.join(course_codes) if course_codes else ''
        
        # Ask for template name
        from PyQt6.QtWidgets import QInputDialog
        template_name, ok = QInputDialog.getText(
            parent_dialog,
            "Save Template",
            f"Enter a name for this template:\n\n(Course code(s) will be added automatically)",
            QLineEdit.EchoMode.Normal,
            ""
        )
        
        if not ok or not template_name.strip():
            return
        
        template_name = template_name.strip()
        
        # Append course code suffix to template name
        template_name_with_suffix = template_name + course_suffix
        
        # Collect all outcomes
        outcomes = []
        for i in range(self.outcome_list.count()):
            item = self.outcome_list.item(i)
            outcome_data = item.data(Qt.ItemDataRole.UserRole)
            outcomes.append(outcome_data)
        
        # Create template data structure
        template = {
            'name': template_name_with_suffix,
            'created_at': datetime.now().isoformat(),
            'outcomes': outcomes
        }
        
        # Save to file
        import json
        from src.utils.resources import get_user_templates_dir
        
        templates_dir = get_user_templates_dir()
        
        # Create safe filename
        safe_name = "".join(c for c in template_name_with_suffix if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        filepath = templates_dir / f"{safe_name}.json"
        
        # Check if file exists
        if filepath.exists():
            reply = QMessageBox.question(
                parent_dialog,
                "Template Exists",
                f"A template named '{template_name_with_suffix}' already exists. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        try:
            with open(filepath, 'w') as f:
                json.dump(template, f, indent=2)
            
            QMessageBox.information(
                parent_dialog,
                "Template Saved",
                f"Template '{template_name_with_suffix}' has been saved successfully!\n\n"
                f"Location: {filepath}"
            )
        except Exception as e:
            QMessageBox.critical(
                parent_dialog,
                "Error Saving Template",
                f"Failed to save template: {str(e)}"
            )
    
    def load_template_dialog(self):
        """Load outcomes from a saved template"""
        import json
        from src.utils.resources import get_user_templates_dir
        
        templates_dir = get_user_templates_dir()
        
        # Get list of template files
        template_files = list(templates_dir.glob('*.json'))
        
        if not template_files:
            QMessageBox.information(
                self,
                "No Templates",
                f"No templates found in:\n{templates_dir}\n\nCreate and save some outcomes first!"
            )
            return
        
        # Load template names
        templates = []
        for filepath in template_files:
            try:
                with open(filepath, 'r') as f:
                    template = json.load(f)
                    templates.append({
                        'name': template.get('name', filepath.stem),
                        'created_at': template.get('created_at', 'Unknown'),
                        'filepath': filepath,
                        'data': template
                    })
            except Exception as e:
                pass
        
        if not templates:
            QMessageBox.warning(
                self,
                "No Valid Templates",
                "No valid templates found."
            )
            return
        
        # Show template selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Template")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        instructions = QLabel("Select a template to load:")
        layout.addWidget(instructions)
        
        template_list = QListWidget()
        for template in templates:
            from datetime import datetime
            try:
                created = datetime.fromisoformat(template['created_at'])
                date_str = created.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = "Unknown date"
            
            item_text = f"{template['name']} (saved {date_str})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, template)
            template_list.addItem(item)
        
        layout.addWidget(template_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(lambda: self.load_selected_template(dialog, template_list))
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda: self.delete_selected_template(dialog, template_list))
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(load_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def load_selected_template(self, dialog, template_list):
        """Load the selected template"""
        current_item = template_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(
                dialog,
                "No Selection",
                "Please select a template to load."
            )
            return
        
        template = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Confirm if there are existing outcomes
        if self.outcome_list.count() > 0:
            reply = QMessageBox.question(
                dialog,
                "Replace Outcomes?",
                "Loading this template will replace your current outcomes. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Clear existing outcomes
        self.outcome_list.clear()
        
        # Load outcomes from template
        outcomes = template['data'].get('outcomes', [])
        
        for outcome_data in outcomes:
            outcome_name = outcome_data.get('name', 'Unknown')
            threshold = outcome_data.get('threshold', 70)
            assignments = outcome_data.get('assignments', [])
            old_parts_config = outcome_data.get('parts_config', {})
            
            # Match assignments by name and rebuild parts_config
            matched_assignments = []
            new_parts_config = {}
            
            # Debug: print what we have
            print(f"Loading outcome: {outcome_name}")
            print(f"Assignments in template: {[a.get('name') for a in assignments]}")
            print(f"old_parts_config keys: {list(old_parts_config.keys())}")
            
            for template_assignment in assignments:
                template_name = template_assignment.get('name')
                template_assignment_id = template_assignment.get('id')
                
                print(f"\nProcessing assignment: {template_name} (template ID: {template_assignment_id})")
                
                # Find matching assignment by name in current courses
                matched = None
                for current_assignment in self.all_assignments:
                    if current_assignment.get('name') == template_name:
                        matched = current_assignment
                        break
                
                if not matched:
                    print(f"  No match found for {template_name}")
                    continue
                    
                matched_assignments.append(matched)
                new_assignment_id = matched.get('id')
                print(f"  Matched to current assignment ID: {new_assignment_id}")
                
                # Find parts for this assignment from old_parts_config
                # Try multiple key formats
                old_parts = None
                for key_variant in [template_assignment_id, str(template_assignment_id), int(template_assignment_id) if isinstance(template_assignment_id, str) and template_assignment_id.isdigit() else None]:
                    if key_variant is not None and key_variant in old_parts_config:
                        old_parts = old_parts_config[key_variant]
                        print(f"  Found old_parts with key: {key_variant}, count: {len(old_parts) if old_parts else 0}")
                        break
                
                # Fallback: if only one assignment, use the only parts entry
                if not old_parts and len(assignments) == 1 and len(old_parts_config) > 0:
                    old_parts = list(old_parts_config.values())[0]
                    print(f"  Using fallback parts (only assignment), count: {len(old_parts) if old_parts else 0}")
                
                if not old_parts or not isinstance(old_parts, list):
                    print(f"  No valid old_parts found")
                    continue
                    
                # Re-discover parts with new Canvas IDs
                print(f"  Re-discovering {len(old_parts)} parts...")
                new_parts = []
                course_ids = matched.get('course_ids', [matched.get('course_id')])
                quiz_ids_by_course = matched.get('quiz_ids_by_course', {})
                
                for old_part in old_parts:
                    print(f"    Processing old_part: {old_part}")
                    if not isinstance(old_part, dict):
                        print(f"      SKIP: Not a dict")
                        continue
                        
                    part_type = old_part.get('type')
                    print(f"      Part type: {part_type}")
                    
                    if part_type == 'quiz_group':
                        # Re-discover this quiz group by name
                        group_name = old_part.get('group_name')
                        groups_by_name = {}
                        
                        for cid in course_ids:
                            qid = quiz_ids_by_course.get(cid) or matched.get('quiz_id')
                            if not qid:
                                continue
                            
                            try:
                                questions = self.canvas_client.get_quiz_questions(cid, qid)
                                group_ids = {q.get('quiz_group_id') for q in questions if q.get('quiz_group_id')}
                                
                                for group_id in group_ids:
                                    try:
                                        response = self.canvas_client.session.get(
                                            f"{self.canvas_client.base_url}/api/v1/courses/{cid}/quizzes/{qid}/groups/{group_id}",
                                            timeout=30
                                        )
                                        if response.status_code == 200:
                                            group = response.json()
                                            current_group_name = group.get('name')
                                            
                                            if current_group_name == group_name:
                                                if group_name not in groups_by_name:
                                                    groups_by_name[group_name] = {
                                                        'group_ids_by_course': {},
                                                        'pick_count_by_course': {},
                                                        'question_points_by_course': {}
                                                    }
                                                groups_by_name[group_name]['group_ids_by_course'][str(cid)] = str(group_id)
                                                groups_by_name[group_name]['pick_count_by_course'][str(cid)] = group.get('pick_count', 0)
                                                groups_by_name[group_name]['question_points_by_course'][str(cid)] = group.get('question_points', 0)
                                    except:
                                        pass
                            except:
                                pass
                        
                        # Add re-discovered group
                        for gname, gdata in groups_by_name.items():
                            new_parts.append({
                                'type': 'quiz_group',
                                'group_name': gname,
                                'group_ids_by_course': gdata['group_ids_by_course'],
                                'pick_count_by_course': gdata['pick_count_by_course'],
                                'question_points_by_course': gdata['question_points_by_course'],
                                'assignment_id': new_assignment_id
                            })
                    
                    elif part_type == 'rubric_criterion':
                        # Re-discover this rubric criterion by description
                        criterion_description = old_part.get('description', '').strip()
                        if not criterion_description:
                            continue
                        
                        print(f"    Re-discovering rubric criterion: {criterion_description}")
                        # Build mapping of criterion IDs across all courses
                        criterion_ids_by_course = {}
                        criterion_points = 0
                        
                        for cid in course_ids:
                            aid = matched.get('assignment_ids_by_course', {}).get(cid, matched.get('id'))
                            
                            try:
                                course_assignment = self.canvas_client.get_assignment(cid, aid)
                                course_rubric = course_assignment.get('rubric', [])
                                print(f"      Course {cid}: Found {len(course_rubric)} rubric criteria")
                                
                                for criterion in course_rubric:
                                    current_description = criterion.get('description', '').strip()
                                    criterion_id = criterion.get('id')
                                    
                                    # Match by description (case-insensitive, trimmed)
                                    if current_description.lower() == criterion_description.lower():
                                        criterion_ids_by_course[str(cid)] = str(criterion_id)
                                        if criterion_points == 0:
                                            criterion_points = criterion.get('points', 0)
                                        print(f"        MATCH: '{current_description}' -> ID {criterion_id}")
                                        break
                            except Exception as e:
                                print(f"      Course {cid}: Error - {e}")
                                pass
                        
                        # Only add if we found criterion in at least one course
                        if criterion_ids_by_course:
                            print(f"      Adding criterion with {len(criterion_ids_by_course)} course mappings")
                            new_parts.append({
                                'type': 'rubric_criterion',
                                'description': criterion_description,
                                'criterion_ids_by_course': criterion_ids_by_course,
                                'points': criterion_points,
                                'assignment_id': new_assignment_id
                            })
                        else:
                            print(f"      WARNING: No criterion found matching '{criterion_description}'")
                
                # Store parts for this assignment
                if new_parts:
                    print(f"  Storing {len(new_parts)} new parts for assignment {new_assignment_id}")
                    new_parts_config[new_assignment_id] = new_parts
                else:
                    print(f"  No parts to store for assignment {new_assignment_id}")
            
            if matched_assignments:
                # Add to outcome list
                outcome_text = f"{outcome_name} ({threshold}%) - {len(matched_assignments)} assignment(s)"
                item = QListWidgetItem(outcome_text)
                
                item.setData(Qt.ItemDataRole.UserRole, {
                    'name': outcome_name,
                    'description': outcome_data.get('description', ''),
                    'threshold': threshold,
                    'assignments': matched_assignments,
                    'parts_config': new_parts_config
                })
                self.outcome_list.addItem(item)
                
                # Also store in outcome_parts_configs
                if new_parts_config:
                    if not hasattr(self, 'outcome_parts_configs'):
                        self.outcome_parts_configs = {}
                    self.outcome_parts_configs[outcome_name] = new_parts_config
        
        dialog.accept()
        
        # Better feedback based on what actually loaded
        if self.outcome_list.count() == 0:
            QMessageBox.warning(
                dialog.parent(),
                "No Matching Assignments",
                f"Template '{template['name']}' could not be loaded.\n\n"
                f"None of the assignments in this template were found in your selected courses.\n\n"
                f"Make sure you've selected the correct courses that contain these assignments:\n" +
                "\n".join(f"  • {a.get('name')}" for outcome in outcomes for a in outcome.get('assignments', [])[:5])
            )
        elif self.outcome_list.count() < len(outcomes):
            QMessageBox.warning(
                dialog.parent(),
                "Partial Template Load",
                f"Template '{template['name']}' partially loaded.\n\n"
                f"Loaded {self.outcome_list.count()} of {len(outcomes)} outcome(s).\n\n"
                f"Some outcomes could not be loaded because their assignments weren't found in your selected courses."
            )
        else:
            QMessageBox.information(
                dialog.parent(),
                "Template Loaded",
                f"Template '{template['name']}' loaded successfully!\n\n"
                f"Loaded {len(outcomes)} outcome(s)."
            )
    
    def delete_selected_template(self, dialog, template_list):
        """Delete the selected template"""
        current_item = template_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(
                dialog,
                "No Selection",
                "Please select a template to delete."
            )
            return
        
        template = current_item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            dialog,
            "Delete Template?",
            f"Are you sure you want to delete template '{template['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                template['filepath'].unlink()
                template_list.takeItem(template_list.row(current_item))
                QMessageBox.information(
                    dialog,
                    "Template Deleted",
                    f"Template '{template['name']}' has been deleted."
                )
            except Exception as e:
                QMessageBox.critical(
                    dialog,
                    "Error",
                    f"Failed to delete template: {str(e)}"
                )
    
    def add_outcome_dialog(self):
        """Show dialog to add a new outcome"""
        from PyQt6.QtWidgets import QFormLayout, QSpinBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Outcome")
        dialog.setMinimumWidth(600)
        
        layout = QFormLayout(dialog)
        
        # Outcome name
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g., Critical Thinking")
        layout.addRow("Outcome Name:", name_input)
        
        # Description
        desc_input = QLineEdit()
        desc_input.setPlaceholderText("e.g., Student demonstrates critical thinking skills")
        layout.addRow("Description:", desc_input)
        
        # Threshold
        threshold_input = QSpinBox()
        threshold_input.setRange(0, 100)
        threshold_input.setValue(70)
        threshold_input.setSuffix("%")
        layout.addRow("Mastery Threshold:", threshold_input)
        
        # Assignment selection
        assignment_label = QLabel("\nSelect assignments that contribute to this outcome:")
        layout.addRow(assignment_label)
        
        assignment_list = QListWidget()
        assignment_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for assignment in self.all_assignments:
            name = assignment.get('name', 'Unnamed')
            points = assignment.get('points_possible', 0)
            course_ids = assignment.get('course_ids', [assignment.get('course_id')])
            
            # Show if assignment is from multiple sections
            if len(course_ids) > 1:
                display_name = f"{name} (from {len(course_ids)} sections, {points} pts)"
            else:
                course = assignment.get('_course_name', '')
                display_name = f"{name} - {course} ({points} pts)"
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, assignment)
            assignment_list.addItem(item)
        layout.addRow(assignment_list)
        
        # Button to configure assignment parts
        configure_parts_btn = QPushButton("⚙️ Configure Assignment Parts")
        configure_parts_btn.clicked.connect(lambda: self.configure_assignment_parts(
            dialog, assignment_list, name_input
        ))
        layout.addRow(configure_parts_btn)
        
        # Initialize assignment parts config for this outcome if not exists
        if not hasattr(self, 'outcome_parts_configs'):
            self.outcome_parts_configs = {}  # {outcome_name: {assignment_id: [parts]}}
        
        # Buttons
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(lambda: self.save_outcome(
            dialog, name_input, desc_input, threshold_input, assignment_list
        ))
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.exec()
    
    def configure_assignment_parts(self, parent_dialog, assignment_list, name_input):
        """Configure which parts of selected assignments to include"""
        # Get outcome name (may not be filled in yet)
        outcome_name = name_input.text().strip()
        if not outcome_name:
            QMessageBox.warning(
                parent_dialog,
                "Missing Outcome Name",
                "Please enter an outcome name first before configuring assignment parts."
            )
            return
        
        # Handle case where name was changed after previous configuration
        if hasattr(self, 'outcome_parts_configs'):
            # Get existing outcome names
            existing_names = set()
            for i in range(self.outcome_list.count()):
                existing_names.add(self.outcome_list.item(i).data(Qt.ItemDataRole.UserRole)['name'])
            
            # If current name not in configs, look for orphaned config to migrate
            if outcome_name not in self.outcome_parts_configs:
                for old_name, config in list(self.outcome_parts_configs.items()):
                    if old_name not in existing_names and config:
                        # Found orphaned config - migrate to current name
                        self.outcome_parts_configs[outcome_name] = config
                        del self.outcome_parts_configs[old_name]
                        break
        
        # Get selected assignments
        selected = []
        for i in range(assignment_list.count()):
            item = assignment_list.item(i)
            if item.isSelected():
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not selected:
            QMessageBox.warning(
                parent_dialog,
                "No Selection",
                "Please select at least one assignment first."
            )
            return
        
        # Show dialog to configure parts
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("Configure Assignment Parts")
        dialog.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(dialog)
        
        instructions = QLabel(
            "Select specific parts of each assignment to include.\n"
            "For quizzes: select question groups\n"
            "For papers: select rubric criteria"
        )
        layout.addWidget(instructions)
        
        # Tab widget for each assignment
        from PyQt6.QtWidgets import QTabWidget, QScrollArea
        tabs = QTabWidget()
        
        for assignment in selected:
            assignment_id = assignment.get('id')
            assignment_name = assignment.get('name', 'Unknown')
            course_id = assignment.get('course_id')
            
            # Get all courses for this assignment (for multi-course assignments)
            course_ids = assignment.get('course_ids', [course_id])
            quiz_ids_by_course = assignment.get('quiz_ids_by_course', {})
            
            # Create tab for this assignment
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            
            # Check if it's a quiz
            quiz_id = assignment.get('quiz_id')
            is_quiz = assignment.get('is_quiz_assignment', False)
            submission_types = assignment.get('submission_types', [])
            
            rubric = assignment.get('rubric')
            
            # Determine if this is actually a quiz with questions
            has_quiz = False
            if quiz_id or is_quiz or 'online_quiz' in submission_types:
                # Check if there are actual quiz IDs in quiz_ids_by_course
                for qid in quiz_ids_by_course.values():
                    if qid:
                        has_quiz = True
                        break
                if not has_quiz and quiz_id:
                    has_quiz = True
            
            # Prioritize: show rubric if it exists and it's not a quiz, otherwise show quiz interface
            if rubric:
                # Paper assignment with rubric
                tab_layout.addWidget(QLabel("Select rubric criteria to include:"))
                
                rubric_list = QListWidget()
                rubric_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
                
                # Collect rubric criteria from ALL courses
                # criterion_description -> {course_id: criterion_id, ...}
                criteria_by_description = {}
                
                for cid in course_ids:
                    # Get rubric for this specific course
                    # Note: assignment.get('rubric') might only be from first course
                    # We need to fetch the assignment details for each course to get accurate rubric IDs
                    aid = assignment.get('assignment_ids_by_course', {}).get(cid, assignment_id)
                    
                    try:
                        course_assignment = self.canvas_client.get_assignment(cid, aid)
                        course_rubric = course_assignment.get('rubric', [])
                        
                        for criterion in course_rubric:
                            criterion_id = criterion.get('id')
                            description = criterion.get('description', 'Unnamed Criterion')
                            points = criterion.get('points', 0)
                            
                            # Store this course's criterion_id under the description
                            if description not in criteria_by_description:
                                criteria_by_description[description] = {
                                    'criterion_ids_by_course': {},
                                    'points': points
                                }
                            criteria_by_description[description]['criterion_ids_by_course'][str(cid)] = str(criterion_id)
                    except Exception as e:
                        # Fallback to using the assignment's rubric (from first course)
                        for criterion in rubric:
                            criterion_id = criterion.get('id')
                            description = criterion.get('description', 'Unnamed Criterion')
                            points = criterion.get('points', 0)
                            
                            if description not in criteria_by_description:
                                criteria_by_description[description] = {
                                    'criterion_ids_by_course': {},
                                    'points': points
                                }
                            criteria_by_description[description]['criterion_ids_by_course'][str(cid)] = str(criterion_id)
                
                # Add items to list - one per unique criterion description
                for description, criterion_data in criteria_by_description.items():
                    course_count = len(criterion_data['criterion_ids_by_course'])
                    item = QListWidgetItem(f"{description} ({criterion_data['points']} pts) - {course_count} course(s)")
                    item.setData(Qt.ItemDataRole.UserRole, {
                        'type': 'rubric_criterion',
                        'description': description,
                        'criterion_ids_by_course': criterion_data['criterion_ids_by_course'],
                        'points': criterion_data['points'],
                        'assignment_id': assignment_id
                    })
                    rubric_list.addItem(item)
                
                # Pre-select previously configured parts
                if hasattr(self, 'outcome_parts_configs') and outcome_name in self.outcome_parts_configs:
                    existing_parts = self.outcome_parts_configs[outcome_name].get(assignment_id, [])
                    for i in range(rubric_list.count()):
                        item = rubric_list.item(i)
                        item_data = item.data(Qt.ItemDataRole.UserRole)
                        for part in existing_parts:
                            if (part.get('type') == 'rubric_criterion' and 
                                part.get('description') == item_data.get('description')):
                                item.setSelected(True)
                                break
                
                tab_layout.addWidget(rubric_list)
                
            if has_quiz:
                # Quiz assignment - show question groups
                tab_layout.addWidget(QLabel("Select question groups to include:"))
                
                questions_list = QListWidget()
                questions_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
                
                # Collect groups from ALL courses
                # group_name -> {course_id: group_id, ...}
                groups_by_name = {}
                
                for cid in course_ids:
                    qid = quiz_ids_by_course.get(cid, quiz_id)
                    if not qid:
                        continue
                    
                    questions = self.canvas_client.get_quiz_questions(cid, qid)
                    
                    # Extract unique group IDs for this course
                    group_ids = set()
                    for q in questions:
                        group_id = q.get('quiz_group_id')
                        if group_id:
                            group_ids.add(group_id)
                    
                    # Fetch details for each group
                    for group_id in group_ids:
                        try:
                            response = self.canvas_client.session.get(
                                f"{self.canvas_client.base_url}/api/v1/courses/{cid}/quizzes/{qid}/groups/{group_id}",
                                timeout=30
                            )
                            
                            if response.status_code == 200:
                                group = response.json()
                                group_name = group.get('name', f'Group {group_id}')
                                pick_count = group.get('pick_count', 0)
                                question_points = group.get('question_points', 0)
                                
                                # Store this course's group_id under the group name
                                if group_name not in groups_by_name:
                                    groups_by_name[group_name] = {
                                        'group_ids_by_course': {},
                                        'pick_count_by_course': {},
                                        'question_points_by_course': {}
                                    }
                                groups_by_name[group_name]['group_ids_by_course'][str(cid)] = str(group_id)
                                groups_by_name[group_name]['pick_count_by_course'][str(cid)] = pick_count
                                groups_by_name[group_name]['question_points_by_course'][str(cid)] = question_points
                        except Exception:
                            pass
                
                # Add items to list - one per unique group name
                for group_name, group_data in groups_by_name.items():
                    course_count = len(group_data['group_ids_by_course'])
                    # Use first course's values for display
                    first_cid = list(group_data['pick_count_by_course'].keys())[0]
                    display_pick = group_data['pick_count_by_course'][first_cid]
                    display_pts = group_data['question_points_by_course'][first_cid]
                    
                    item = QListWidgetItem(
                        f"{group_name} ({display_pick} questions, {display_pts} pts each) - {course_count} course(s)"
                    )
                    item.setData(Qt.ItemDataRole.UserRole, {
                        'type': 'quiz_group',
                        'group_name': group_name,
                        'group_ids_by_course': group_data['group_ids_by_course'],
                        'pick_count_by_course': group_data['pick_count_by_course'],
                        'question_points_by_course': group_data['question_points_by_course'],
                        'assignment_id': assignment_id
                    })
                    questions_list.addItem(item)
                
                # If no groups found
                if not groups_by_name:
                    item = QListWidgetItem(f"All Questions")
                    item.setData(Qt.ItemDataRole.UserRole, {
                        'type': 'all_questions',
                        'assignment_id': assignment_id
                    })
                    questions_list.addItem(item)
                
                # Pre-select previously configured parts
                if hasattr(self, 'outcome_parts_configs') and outcome_name in self.outcome_parts_configs:
                    existing_parts = self.outcome_parts_configs[outcome_name].get(assignment_id, [])
                    for i in range(questions_list.count()):
                        item = questions_list.item(i)
                        item_data = item.data(Qt.ItemDataRole.UserRole)
                        for part in existing_parts:
                            if (part.get('type') == 'quiz_group' and 
                                part.get('group_name') == item_data.get('group_name')):
                                item.setSelected(True)
                                break
                            elif part.get('type') == 'all_questions' and item_data.get('type') == 'all_questions':
                                item.setSelected(True)
                                break
                
                tab_layout.addWidget(questions_list)
                
            else:
                # Regular assignment without quiz or rubric
                tab_layout.addWidget(QLabel(
                    "This assignment doesn't have quizzes or rubrics.\n"
                    "The entire assignment will be used."
                ))
            
            tabs.addTab(tab, assignment_name)
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(lambda: self.save_parts_config(dialog, tabs, selected, outcome_name))
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def save_parts_config(self, dialog, tabs, assignments, outcome_name):
        """Save the configuration of assignment parts for this outcome"""
        # Initialize storage for this outcome
        if outcome_name not in self.outcome_parts_configs:
            self.outcome_parts_configs[outcome_name] = {}
        
        # Extract selected parts from each tab
        for i in range(tabs.count()):
            tab = tabs.widget(i)
            assignment = assignments[i]
            assignment_id = assignment.get('id')
            
            # Find the list widget in this tab
            list_widget = None
            for child in tab.findChildren(QListWidget):
                list_widget = child
                break
            
            if list_widget:
                selected_parts = []
                for j in range(list_widget.count()):
                    item = list_widget.item(j)
                    if item.isSelected():
                        part_data = item.data(Qt.ItemDataRole.UserRole)
                        selected_parts.append(part_data)
                
                if selected_parts:
                    self.outcome_parts_configs[outcome_name][assignment_id] = selected_parts
        
        dialog.accept()
        QMessageBox.information(
            dialog.parent(),
            "Configuration Saved",
            f"Assignment parts configured for outcome '{outcome_name}': "
            f"{len(self.outcome_parts_configs[outcome_name])} assignment(s)."
        )
    
    def edit_outcome(self, item):
        """Edit an existing outcome"""
        outcome_data = item.data(Qt.ItemDataRole.UserRole)
        old_name = outcome_data['name']
        
        # Open the same dialog as add_outcome but pre-filled
        from PyQt6.QtWidgets import QFormLayout, QSpinBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Outcome")
        dialog.setMinimumWidth(600)
        
        layout = QFormLayout(dialog)
        
        # Outcome name (pre-filled)
        name_input = QLineEdit()
        name_input.setText(old_name)
        name_input.setPlaceholderText("e.g., Critical Thinking")
        layout.addRow("Outcome Name:", name_input)
        
        # Description (pre-filled)
        desc_input = QLineEdit()
        desc_input.setText(outcome_data.get('description', ''))
        desc_input.setPlaceholderText("e.g., Student demonstrates critical thinking skills")
        layout.addRow("Description:", desc_input)
        
        # Threshold (pre-filled)
        threshold_input = QSpinBox()
        threshold_input.setRange(0, 100)
        threshold_input.setValue(outcome_data['threshold'])
        threshold_input.setSuffix("%")
        layout.addRow("Mastery Threshold:", threshold_input)
        
        # Assignment selection (pre-selected)
        assignment_label = QLabel("\nSelect assignments that contribute to this outcome:")
        layout.addRow(assignment_label)
        
        assignment_list = QListWidget()
        assignment_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        # Get currently selected assignment IDs (normalize to strings for comparison)
        current_assignment_ids = set()
        for a in outcome_data['assignments']:
            aid = a.get('id')
            if aid is not None:
                current_assignment_ids.add(str(aid))
        
        print(f"DEBUG edit_outcome: current_assignment_ids = {current_assignment_ids}")
        
        items_to_select = []
        for assignment in self.all_assignments:
            name = assignment.get('name', 'Unnamed')
            points = assignment.get('points_possible', 0)
            course_ids = assignment.get('course_ids', [assignment.get('course_id')])
            assignment_id = str(assignment.get('id'))
            
            # Show if assignment is from multiple sections
            if len(course_ids) > 1:
                display_name = f"{name} (from {len(course_ids)} sections, {points} pts)"
            else:
                course = assignment.get('_course_name', '')
                display_name = f"{name} - {course} ({points} pts)"
            
            item_widget = QListWidgetItem(display_name)
            item_widget.setData(Qt.ItemDataRole.UserRole, assignment)
            assignment_list.addItem(item_widget)
            
            # Track items to select
            if assignment_id in current_assignment_ids:
                print(f"DEBUG: Will pre-select assignment: {name} (ID: {assignment_id})")
                items_to_select.append(assignment_list.count() - 1)
        
        layout.addRow(assignment_list)
        
        # Now select items after they're added to the list
        for index in items_to_select:
            item = assignment_list.item(index)
            item.setSelected(True)
            assignment_list.setCurrentItem(item)  # Force visual update
        
        # Load existing parts config into temporary storage
        existing_parts = outcome_data.get('parts_config', {})
        if existing_parts:
            # Temporarily store under old name so configure button can access it
            if not hasattr(self, 'outcome_parts_configs'):
                self.outcome_parts_configs = {}
            self.outcome_parts_configs[old_name] = existing_parts
        
        # Button to configure assignment parts
        configure_parts_btn = QPushButton("⚙️ Configure Assignment Parts")
        
        # Show how many parts are configured
        if existing_parts:
            parts_count = sum(len(parts) for parts in existing_parts.values())
            configure_parts_btn.setText(f"⚙️ Configure Assignment Parts ({parts_count} configured)")
        
        configure_parts_btn.clicked.connect(lambda: self.configure_assignment_parts(
            dialog, assignment_list, name_input
        ))
        layout.addRow(configure_parts_btn)
        
        # Buttons
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(lambda: self.update_outcome(
            dialog, item, name_input, desc_input, threshold_input, assignment_list, old_name
        ))
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.exec()
    
    def update_outcome(self, dialog, list_item, name_input, desc_input, threshold_input, assignment_list, old_name):
        """Update an existing outcome"""
        new_name = name_input.text().strip()
        description = desc_input.text().strip()
        threshold = threshold_input.value()
        
        if not new_name:
            QMessageBox.warning(dialog, "Missing Name", "Please enter an outcome name.")
            return
        
        # Get selected assignments
        selected = []
        for i in range(assignment_list.count()):
            item = assignment_list.item(i)
            if item.isSelected():
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not selected:
            QMessageBox.warning(dialog, "No Assignments", "Please select at least one assignment.")
            return
        
        # Handle parts config - use the name from the dialog (could be old or new)
        # The configure_assignment_parts always uses name_input.text() as the key
        parts_config = {}
        if hasattr(self, 'outcome_parts_configs'):
            # Check both old and new names
            if old_name in self.outcome_parts_configs:
                parts_config = self.outcome_parts_configs[old_name]
            if new_name in self.outcome_parts_configs and new_name != old_name:
                parts_config = self.outcome_parts_configs[new_name]
            
            # If name changed, clean up old entry
            if old_name != new_name and old_name in self.outcome_parts_configs:
                self.outcome_parts_configs[new_name] = self.outcome_parts_configs[old_name]
                del self.outcome_parts_configs[old_name]
                parts_config = self.outcome_parts_configs[new_name]
        
        # Update the list item
        outcome_text = f"{new_name} ({threshold}%) - {len(selected)} assignment(s)"
        list_item.setText(outcome_text)
        
        list_item.setData(Qt.ItemDataRole.UserRole, {
            'name': new_name,
            'description': description,
            'threshold': threshold,
            'assignments': selected,
            'parts_config': parts_config
        })
        
        dialog.accept()
    
    def save_outcome(self, dialog, name_input, desc_input, threshold_input, assignment_list):
        """Save the created outcome"""
        name = name_input.text().strip()
        description = desc_input.text().strip()
        threshold = threshold_input.value()
        
        if not name:
            QMessageBox.warning(dialog, "Missing Name", "Please enter an outcome name.")
            return
        
        # Get selected assignments
        selected = []
        for i in range(assignment_list.count()):
            item = assignment_list.item(i)
            if item.isSelected():
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not selected:
            QMessageBox.warning(dialog, "No Assignments", "Please select at least one assignment.")
            return
        
        # Add to outcome list
        outcome_text = f"{name} ({threshold}%) - {len(selected)} assignment(s)"
        item = QListWidgetItem(outcome_text)
        
        # Get parts config - handle case where user renamed after configuring
        parts_config = {}
        if hasattr(self, 'outcome_parts_configs'):
            # First check if config exists under current name
            if name in self.outcome_parts_configs:
                parts_config = self.outcome_parts_configs[name]
            else:
                # Name might have changed - find any config not used by existing outcomes
                existing_names = set()
                for i in range(self.outcome_list.count()):
                    existing_names.add(self.outcome_list.item(i).data(Qt.ItemDataRole.UserRole)['name'])
                
                # Find unused config (was created during this dialog but name changed)
                for old_name, config in list(self.outcome_parts_configs.items()):
                    if old_name not in existing_names and config:
                        # Found it - move to new name
                        parts_config = config
                        self.outcome_parts_configs[name] = config
                        del self.outcome_parts_configs[old_name]
                        break
        
        item.setData(Qt.ItemDataRole.UserRole, {
            'name': name,
            'description': description,
            'threshold': threshold,
            'assignments': selected,
            'parts_config': parts_config  # Store which parts to use
        })
        self.outcome_list.addItem(item)
        
        dialog.accept()
    
    def generate_report_from_outcomes(self, dialog):
        """Generate report with configured outcomes"""
        if self.outcome_list.count() == 0:
            QMessageBox.warning(
                dialog,
                "No Outcomes",
                "Please create at least one outcome before generating a report."
            )
            return
        
        dialog.accept()
        
        # Collect outcomes
        outcomes = []
        for i in range(self.outcome_list.count()):
            item = self.outcome_list.item(i)
            outcomes.append(item.data(Qt.ItemDataRole.UserRole))
        
        # Show progress
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            # Fetch student data and generate report
            self.fetch_data_and_generate_report(outcomes)
            
        except Exception as e:
            import traceback
            QApplication.restoreOverrideCursor()
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Error generating report:\n{str(e)}"
            )
    
    def fetch_data_and_generate_report(self, outcomes):
        """Fetch student data and generate Excel report - OPTIMIZED"""
        import pandas as pd
        from datetime import datetime
        from PyQt6.QtWidgets import QProgressDialog, QFileDialog
        from PyQt6.QtCore import Qt
        
        # Create progress dialog
        progress = QProgressDialog("Generating report...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        # Get unique course IDs from assignments
        course_ids = set()
        all_assignment_ids = set()
        for outcome in outcomes:
            for assignment in outcome['assignments']:
                # Handle both course_ids (list) and course_id (single)
                assignment_course_ids = assignment.get('course_ids', [])
                if not assignment_course_ids:
                    # Fallback to singular course_id
                    single_id = assignment.get('course_id')
                    if single_id:
                        assignment_course_ids = [single_id]
                
                for cid in assignment_course_ids:
                    course_ids.add(cid)
                
                assignment_id = assignment.get('id')
                if assignment_id:
                    all_assignment_ids.add(assignment_id)
        
        # If course_id not in assignment, get from course_info
        if not course_ids:
            course_ids = set(c['id'] for c in self.course_info)
        
        progress.setLabelText("Fetching students...")
        progress.setValue(10)
        QApplication.processEvents()
        
        # Fetch all students from all courses
        all_students = {}
        student_courses = {}  # Track which courses each student is enrolled in: {student_id: [course_ids]}
        for course_id in course_ids:
            enrollments = self.canvas_client.get_enrollments(course_id)
            for enrollment in enrollments:
                user = enrollment.get('user', {})
                student_id = user.get('id')
                if student_id:
                    if student_id not in all_students:
                        all_students[student_id] = {
                            'id': student_id,
                            'name': user.get('name', 'Unknown'),
                            'sortable_name': user.get('sortable_name', 'Unknown')
                        }
                    # Track all courses this student is enrolled in
                    if student_id not in student_courses:
                        student_courses[student_id] = []
                    student_courses[student_id].append(course_id)
        
        if not all_students:
            progress.close()
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                "No Students Found",
                "No students found in the selected courses.\n"
                "Make sure students are enrolled in these courses."
            )
            return
        
        progress.setLabelText("Fetching assignment submissions...")
        progress.setValue(20)
        QApplication.processEvents()
        
        # Fetch submissions - organized by student's actual enrolled course
        # Structure: {assignment_id: {student_id: score}}
        all_submissions = {}
        
        total_assignments = len(all_assignment_ids)
        for idx, outcome in enumerate(outcomes):
            for assignment in outcome['assignments']:
                assignment_id = assignment.get('id')  # This is just for the dict key
                course_ids_list = assignment.get('course_ids', [assignment.get('course_id')])
                assignment_ids_by_course = assignment.get('assignment_ids_by_course', {})
                
                if assignment_id not in all_submissions:
                    all_submissions[assignment_id] = {}
                    
                    # For each course this assignment appears in
                    for course_id in course_ids_list:
                        # CRITICAL: Use the correct assignment_id for THIS course
                        course_assignment_id = assignment_ids_by_course.get(course_id, assignment_id)
                        submissions = self.canvas_client.get_submissions(course_id, course_assignment_id)
                        
                        # Only store submissions for students enrolled in THIS specific course
                        for submission in submissions:
                            student_id = submission.get('user_id')
                            score = submission.get('score')
                            workflow_state = submission.get('workflow_state', '')
                            
                            is_enrolled = student_id in student_courses and course_id in student_courses[student_id]
                            
                            # Check: is this student enrolled in THIS course?
                            if is_enrolled:
                                # Only store graded submissions with actual scores
                                if workflow_state == 'graded' and score is not None:
                                    all_submissions[assignment_id][student_id] = score
            
            # Update progress
            current = 20 + int((idx / len(outcomes)) * 15)
            progress.setValue(current)
            progress.setLabelText(f"Fetching submissions... ({idx + 1}/{len(outcomes)} outcomes)")
            QApplication.processEvents()
            
            if progress.wasCanceled():
                QApplication.restoreOverrideCursor()
                return
        
        # ============ NEW: PRE-FETCH QUIZ DATA ============
        progress.setLabelText("Pre-fetching quiz data...")
        progress.setValue(35)
        QApplication.processEvents()
        
        all_quiz_data = {}  # {(course_id, quiz_id, student_id): {group_id: [question_data]}}
        
        quiz_assignments = []
        for outcome in outcomes:
            for assignment in outcome['assignments']:
                quiz_ids_by_course = assignment.get('quiz_ids_by_course', {})
                if quiz_ids_by_course:
                    quiz_assignments.append((assignment, quiz_ids_by_course))
        
        for idx, (assignment, quiz_ids_by_course) in enumerate(quiz_assignments):
            course_ids_list = assignment.get('course_ids', [])
            
            for course_id in course_ids_list:
                course_quiz_id = quiz_ids_by_course.get(course_id)
                if not course_quiz_id:
                    continue
                
                # Get all quiz submissions for this course
                quiz_subs = self.canvas_client.get_quiz_submissions(course_id, course_quiz_id)
                
                for quiz_sub in quiz_subs:
                    student_id = quiz_sub.get('user_id')
                    
                    # Only fetch for enrolled students
                    if student_id not in student_courses or course_id not in student_courses[student_id]:
                        continue
                    
                    sub_id = quiz_sub.get('id')
                    questions = self.canvas_client.get_quiz_submission_questions(sub_id)
                    
                    # Organize by group
                    key = (course_id, course_quiz_id, student_id)
                    if key not in all_quiz_data:
                        all_quiz_data[key] = {}
                    
                    for q in questions:
                        if not isinstance(q, dict):
                            continue
                        group_id = q.get('quiz_group_id')
                        if group_id:
                            group_id = str(group_id)
                            if group_id not in all_quiz_data[key]:
                                all_quiz_data[key][group_id] = []
                            all_quiz_data[key][group_id].append(q)
            
            current = 35 + int((idx / len(quiz_assignments)) * 20) if quiz_assignments else 35
            progress.setValue(current)
            progress.setLabelText(f"Pre-fetching quiz data... ({idx + 1}/{len(quiz_assignments)} quizzes)")
            QApplication.processEvents()
        
        # ============ NEW: PRE-FETCH RUBRIC DATA ============
        progress.setLabelText("Pre-fetching rubric data...")
        progress.setValue(55)
        QApplication.processEvents()
        
        all_rubric_data = {}  # {(course_id, assignment_id, student_id): rubric_assessment}
        
        rubric_assignments = []
        for outcome in outcomes:
            parts_config = outcome.get('parts_config', {})
            for assignment in outcome['assignments']:
                assignment_id = assignment.get('id')
                if assignment_id in parts_config:
                    selected_parts = parts_config[assignment_id]
                    if any(p.get('type') == 'rubric_criterion' for p in selected_parts if isinstance(p, dict)):
                        rubric_assignments.append(assignment)
        
        for idx, assignment in enumerate(rubric_assignments):
            assignment_id = assignment.get('id')
            course_ids_list = assignment.get('course_ids', [])
            assignment_ids_by_course = assignment.get('assignment_ids_by_course', {})
            
            for course_id in course_ids_list:
                course_assignment_id = assignment_ids_by_course.get(course_id, assignment_id)
                submissions = self.canvas_client.get_submissions(course_id, course_assignment_id)
                
                for submission in submissions:
                    student_id = submission.get('user_id')
                    
                    # Only store for enrolled students
                    if student_id not in student_courses or course_id not in student_courses[student_id]:
                        continue
                    
                    rubric_assessment = submission.get('rubric_assessment', {})
                    if rubric_assessment:
                        key = (course_id, course_assignment_id, student_id)
                        all_rubric_data[key] = rubric_assessment
            
            current = 55 + int((idx / len(rubric_assignments)) * 15) if rubric_assignments else 55
            progress.setValue(current)
            progress.setLabelText(f"Pre-fetching rubric data... ({idx + 1}/{len(rubric_assignments)} assignments)")
            QApplication.processEvents()
        
        progress.setLabelText("Calculating outcome scores...")
        progress.setValue(70)
        QApplication.processEvents()
        
        # Build data structure for report
        report_data = []
        
        for student_idx, (student_id, student) in enumerate(all_students.items()):
            if progress.wasCanceled():
                QApplication.restoreOverrideCursor()
                return
            
            row = {
                'Student ID': student_id,
                'Student Name': student['sortable_name'],
                'Course ID': student_courses.get(student_id, [None])[0]  # First course they're enrolled in
            }
            
            # Calculate score for each outcome
            for outcome in outcomes:
                outcome_name = outcome['name']
                parts_config = outcome.get('parts_config', {})
                total_earned = 0
                total_possible = 0
                
                # Get scores from each assignment in this outcome
                for assignment in outcome['assignments']:
                    assignment_id = assignment.get('id')
                    assignment_name = assignment.get('name', 'Unknown')
                    assignment_possible = assignment.get('points_possible', 0)
                    course_ids_list = assignment.get('course_ids', [assignment.get('course_id')])
                    assignment_ids_by_course = assignment.get('assignment_ids_by_course', {})
                    quiz_ids_by_course = assignment.get('quiz_ids_by_course', {})
                    
                    # Check if this assignment has parts configured
                    if assignment_id in parts_config:
                        # Assignment has specific parts selected
                        selected_parts = parts_config[assignment_id]
                        
                        # Calculate score from selected parts only
                        part_score = 0
                        part_possible = 0
                        
                        # Ensure selected_parts is a list
                        if not isinstance(selected_parts, list):
                            # Fall back to full assignment score
                            student_score = all_submissions.get(assignment_id, {}).get(student_id, None)
                            if student_score is not None:
                                row[f"{assignment_name}"] = student_score
                                total_earned += student_score
                                total_possible += assignment_possible
                            else:
                                row[f"{assignment_name}"] = None
                            continue
                        
                        for part in selected_parts:
                            if not isinstance(part, dict):
                                continue
                                
                            part_type = part.get('type')
                            
                            if part_type == 'quiz_group':
                                # ============ CHANGED: LOOKUP CACHED QUIZ DATA ============
                                group_ids_by_course = part.get('group_ids_by_course', {})
                                pick_count_by_course = part.get('pick_count_by_course', {})
                                question_points_by_course = part.get('question_points_by_course', {})
                                
                                student_course_ids = student_courses.get(student_id, [])
                                relevant_courses = [cid for cid in course_ids_list if cid in student_course_ids]
                                
                                found_submission = False
                                for course_id in relevant_courses:
                                    group_id = group_ids_by_course.get(str(course_id))
                                    if not group_id:
                                        continue
                                    
                                    group_id = str(group_id)
                                    
                                    course_quiz_id = quiz_ids_by_course.get(course_id)
                                    if not course_quiz_id:
                                        continue
                                    
                                    # Lookup in cached data instead of API call
                                    key = (course_id, course_quiz_id, student_id)
                                    if key in all_quiz_data and group_id in all_quiz_data[key]:
                                        questions = all_quiz_data[key][group_id]
                                        
                                        # Use actual number of questions student answered, not pick_count
                                        actual_question_count = len(questions)
                                        question_points = question_points_by_course.get(str(course_id), 0)

                                        correct_count = 0
                                        for q in questions:
                                            if q.get('correct') in ['true', True]:
                                                correct_count += 1

                                        part_score += correct_count * question_points
                                        part_possible += actual_question_count * question_points  # Use actual count
                                        found_submission = True
                                        break
                            
                            elif part_type == 'rubric_criterion':
                                # ============ CHANGED: LOOKUP CACHED RUBRIC DATA ============
                                criterion_ids_by_course = part.get('criterion_ids_by_course', {})
                                criterion_description = part.get('description', 'Unknown')
                                criterion_points_possible = part.get('points', 0)
                                
                                student_course_ids = student_courses.get(student_id, [])
                                relevant_courses = [cid for cid in course_ids_list if cid in student_course_ids]
                                
                                found_submission = False
                                for course_id in relevant_courses:
                                    criterion_id = criterion_ids_by_course.get(str(course_id))
                                    if not criterion_id:
                                        continue
                                    
                                    course_assignment_id = assignment_ids_by_course.get(course_id, assignment_id)
                                    
                                    # Lookup in cached data instead of API call
                                    key = (course_id, course_assignment_id, student_id)
                                    if key in all_rubric_data:
                                        rubric_assessment = all_rubric_data[key]
                                        
                                        if criterion_id in rubric_assessment:
                                            criterion_data = rubric_assessment[criterion_id]
                                            criterion_score = criterion_data.get('points', 0)
                                            part_score += criterion_score
                                            part_possible += criterion_points_possible
                                            found_submission = True
                                        elif str(criterion_id) in rubric_assessment:
                                            criterion_data = rubric_assessment[str(criterion_id)]
                                            criterion_score = criterion_data.get('points', 0)
                                            part_score += criterion_score
                                            part_possible += criterion_points_possible
                                            found_submission = True
                                        
                                        if found_submission:
                                            break
                        
                        # Use part score with unique column name (outcome prefix to avoid duplicates)
                        column_name = f"{outcome_name} - {assignment_name}"
                        
                        # Only write the score if we actually found parts data
                        if part_possible > 0 or part_score > 0:
                            row[column_name] = part_score
                            total_earned += part_score
                            total_possible += part_possible
                        else:
                            # No parts data found - leave as None
                            row[column_name] = None
                        
                    else:
                        # No parts configured - use full assignment score
                        student_score = all_submissions.get(assignment_id, {}).get(student_id, None)
                        
                        if student_score is not None:
                            column_name = f"{outcome_name} - {assignment_name}"
                            row[column_name] = student_score
                            total_earned += student_score
                            total_possible += assignment_possible
                        else:
                            column_name = f"{outcome_name} - {assignment_name}"
                            row[column_name] = None
                
                # Calculate percentage for outcome
                if total_possible > 0:
                    percentage = (total_earned / total_possible) * 100
                else:
                    percentage = 0
                
                row[f"{outcome_name} Total (%)"] = round(percentage)
                row[f"{outcome_name} Status"] = "Met" if percentage >= outcome['threshold'] else "Not Met"
            
            report_data.append(row)
            
            # Update progress
            current = 70 + int((student_idx / len(all_students)) * 20)
            progress.setValue(current)
            QApplication.processEvents()
        
        progress.setLabelText("Creating Excel file...")
        progress.setValue(90)
        QApplication.processEvents()
        
        # Create DataFrame
        df = pd.DataFrame(report_data)
        
        # Check if we have data
        if df.empty:
            progress.close()
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                "No Data",
                "No student data found. Make sure:\n"
                "1. Students are enrolled in the selected courses\n"
                "2. Students have submitted the selected assignments"
            )
            return
        
        # Sort by student name if column exists
        if 'Student Name' in df.columns:
            df = df.sort_values('Student Name')
        
        # Generate filename with course code prefix
        # Extract course code from first course (e.g., "PSY3421")
        course_code = "Course"
        if self.course_info:
            first_course_name = self.course_info[0].get('name', '')
            # Try to extract course code (letters + numbers at start)
            import re
            match = re.match(r'^([A-Z]+\s*\d+)', first_course_name)
            if match:
                course_code = match.group(1).replace(' ', '')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{course_code}_outcome_report_{timestamp}.xlsx"
        
        # Let user choose where to save
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            str(Path.home() / "Desktop" / default_filename),
            "Excel Files (*.xlsx)"
        )
        
        if not filepath:
            # User cancelled
            progress.close()
            QApplication.restoreOverrideCursor()
            return
        
        filepath = Path(filepath)
        
        # Write to Excel
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Outcome Report', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Outcome Report']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        progress.setValue(100)
        progress.close()
        QApplication.restoreOverrideCursor()
        
        # Show success message
        result = QMessageBox.information(
            self,
            "Report Generated",
            f"Report generated successfully!\n\n"
            f"File: {filepath.name}\n"
            f"Location: {filepath.parent}\n"
            f"Students: {len(all_students)}\n"
            f"Outcomes: {len(outcomes)}\n\n"
            f"Would you like to open the report folder?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            import subprocess
            import platform
            if platform.system() == 'Windows':
                subprocess.run(['explorer', str(filepath.parent)])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(filepath.parent)])
            else:  # Linux
                subprocess.run(['xdg-open', str(filepath.parent)])


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
