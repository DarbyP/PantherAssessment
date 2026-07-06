"""
Panther Assessment - Outcome Dialog Mixin
Outcome management methods for MainWindow
"""

import json
import re
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QMessageBox,
    QApplication, QLineEdit, QComboBox, QWidget, QTabWidget,
    QScrollArea, QFormLayout, QSpinBox, QDialogButtonBox, QInputDialog
)
from PyQt6.QtCore import Qt
from src.utils.resources import get_user_templates_dir

class OutcomeDialogMixin:
    """Mixin providing outcome management dialogs for MainWindow"""

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

        delete_outcome_btn = QPushButton("🗑 Delete Outcome")
        def delete_selected_outcome():
            selected = self.outcome_list.selectedItems()
            if not selected:
                QMessageBox.warning(dialog, "No Selection", "Please select an outcome to delete.")
                return
            reply = QMessageBox.question(
                dialog, "Delete Outcome",
                f"Delete outcome '{selected[0].text()}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.outcome_list.takeItem(self.outcome_list.row(selected[0]))
        delete_outcome_btn.clicked.connect(delete_selected_outcome)
        outcome_layout.addWidget(delete_outcome_btn)
        
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
        save_template_btn.clicked.connect(self.save_as_template)
        
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
        
        # If a template is currently loaded, offer to update it
        from PyQt6.QtWidgets import QInputDialog
        loaded_filepath = getattr(self, '_loaded_template_filepath', None)
        loaded_name = getattr(self, '_loaded_template_name', None)

        if loaded_filepath and loaded_filepath.exists():
            reply = QMessageBox.question(
                parent_dialog,
                "Update Template",
                f"Update the currently loaded template '{loaded_name}'?\n\nClick No to save as a new template.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                # Overwrite loaded template directly
                outcomes = []
                for i in range(self.outcome_list.count()):
                    item = self.outcome_list.item(i)
                    outcomes.append(item.data(Qt.ItemDataRole.UserRole))
                import json
                from datetime import datetime
                template_data = {
                    'name': loaded_name,
                    'created_at': datetime.now().isoformat(),
                    'outcomes': outcomes
                }
                try:
                    with open(loaded_filepath, 'w') as f:
                        json.dump(template_data, f, indent=2)
                    QMessageBox.information(parent_dialog, "Template Updated",
                        f"Template '{loaded_name}' has been updated.")
                except Exception as e:
                    QMessageBox.critical(parent_dialog, "Error", f"Failed to update template: {str(e)}")
                return

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
        
        # Track the loaded template for overwrite support
        self._loaded_template_filepath = template.get('filepath')
        self._loaded_template_name = template.get('name')

        # Clear existing outcomes
        self.outcome_list.clear()

        # Load outcomes from template
        outcomes = template['data'].get('outcomes', [])
        
        for outcome_data in outcomes:
            outcome_name = outcome_data.get('name', 'Unknown')
            assignments = outcome_data.get('assignments', [])
            old_parts_config = outcome_data.get('parts_config', {})
            
            # Match assignments by name and rebuild parts_config
            matched_assignments = []
            new_parts_config = {}
            
            # Debug: print what we have
            for template_assignment in assignments:
                template_name = template_assignment.get('name')
                template_assignment_id = template_assignment.get('id')
                # Find matching assignment by name in current courses
                matched = None
                for current_assignment in self.all_assignments:
                    if current_assignment.get('name') == template_name:
                        matched = current_assignment
                        break
                
                if not matched:
                    continue
                    
                matched_assignments.append(matched)
                new_assignment_id = matched.get('id')
                # Find parts for this assignment from old_parts_config
                # Try multiple key formats
                old_parts = None
                for key_variant in [template_assignment_id, str(template_assignment_id), int(template_assignment_id) if isinstance(template_assignment_id, str) and template_assignment_id.isdigit() else None]:
                    if key_variant is not None and key_variant in old_parts_config:
                        old_parts = old_parts_config[key_variant]
                        break
                
                # Fallback: if only one assignment, use the only parts entry
                if not old_parts and len(assignments) == 1 and len(old_parts_config) > 0:
                    old_parts = list(old_parts_config.values())[0]

                # If no parts configured, still include the assignment (use full score)
                if not old_parts or not isinstance(old_parts, list):
                    matched_assignments.append(matched)
                    continue

                # Re-discover parts with new Canvas IDs
                new_parts = []
                course_ids = matched.get('course_ids', [matched.get('course_id')])
                quiz_ids_by_course = matched.get('quiz_ids_by_course', {})
                
                for old_part in old_parts:
                    if not isinstance(old_part, dict):
                        continue
                        
                    part_type = old_part.get('type')
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
                        # Build mapping of criterion IDs across all courses
                        criterion_ids_by_course = {}
                        criterion_points = 0
                        
                        for cid in course_ids:
                            aid = matched.get('assignment_ids_by_course', {}).get(cid, matched.get('id'))
                            
                            try:
                                course_assignment = self.canvas_client.get_assignment(cid, aid)
                                course_rubric = course_assignment.get('rubric', [])
                                for criterion in course_rubric:
                                    current_description = criterion.get('description', '').strip()
                                    criterion_id = criterion.get('id')
                                    
                                    # Match by description (case-insensitive, trimmed)
                                    if current_description.lower() == criterion_description.lower():
                                        criterion_ids_by_course[str(cid)] = str(criterion_id)
                                        if criterion_points == 0:
                                            criterion_points = criterion.get('points', 0)
                                        break
                            except Exception as e:
                                pass
                        
                        # Only add if we found criterion in at least one course
                        if criterion_ids_by_course:
                            new_parts.append({
                                'type': 'rubric_criterion',
                                'description': criterion_description,
                                'criterion_ids_by_course': criterion_ids_by_course,
                                'points': criterion_points,
                                'assignment_id': new_assignment_id
                            })
                        else:
                            pass
                # Store parts for this assignment
                if new_parts:
                    new_parts_config[new_assignment_id] = new_parts
                else:
                    pass
            if matched_assignments:
                # Add to outcome list
                outcome_text = outcome_name
                item = QListWidgetItem(outcome_text)
                
                item.setData(Qt.ItemDataRole.UserRole, {
                    'name': outcome_name,
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
        total_sections = len(self.course_info)

        # Outcome name
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g., Critical Thinking")
        layout.addRow("Outcome Name:", name_input)
        
        name_note = QLabel("<i>Note: The outcome name becomes the column header in the Total % tab. Use the same name as in your assessment master file.</i>")
        name_note.setWordWrap(True)
        from src.utils.theme import get_palette, is_dark_mode
        from src.utils.config import get_config
        _cfg = get_config()
        _p = get_palette(_cfg.primary_color, _cfg.secondary_color, is_dark_mode())
        name_note.setStyleSheet(f"color: {_p['text_muted']}; font-size: 13px;")
        layout.addRow(name_note)
        
        # Threshold

        
        # Assignment selection
        assignment_label = QLabel("\nSelect assignments that contribute to this outcome:")
        layout.addRow(assignment_label)

        if total_sections > 1:
            legend = QLabel(
                '<font color="#2E7D32">■ All sections</font> &nbsp;&nbsp;'
                '<font color="#E65100">■ Some sections</font> &nbsp;&nbsp;'
                '<font color="#6A0DAD">■ One section only</font>'
            )
            legend.setStyleSheet("font-size: 12px;")
            layout.addRow(legend)
        
        from PyQt6.QtGui import QColor

        assignment_list = QListWidget()
        assignment_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for assignment in self.all_assignments:
            name = assignment.get('name', 'Unnamed')
            points = assignment.get('points_possible', 0)
            course_ids = assignment.get('course_ids', [assignment.get('course_id')])
            names_by_id = assignment.get('_course_names_by_id', {})
            count = len(course_ids)

            if total_sections <= 1:
                # Single course selected — plain black, no section info needed
                display_name = f"{name} ({points} pts)"
                color = None
            elif count == total_sections:
                # All sections
                display_name = f"{name} (all sections, {points} pts)"
                color = QColor("#2E7D32")  # Green
            elif count == 1:
                # Unique to one section
                label = list(names_by_id.values())[0] if names_by_id else ''
                display_name = f"{name} ({label}, {points} pts)"
                color = QColor("#6A0DAD")  # Purple
            else:
                # Some sections
                labels = ', '.join(names_by_id.get(cid, str(cid)) for cid in course_ids)
                display_name = f"{name} ({labels} — {count} of {total_sections} sections, {points} pts)"
                color = QColor("#E65100")  # Orange

            item = QListWidgetItem(display_name)
            if color:
                item.setForeground(color)
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
            dialog, name_input, assignment_list
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
                
            if not rubric and not has_quiz:
                # Regular assignment without quiz or rubric
                tab_layout.addWidget(QLabel(
                    "This assignment doesn't have quizzes or rubrics.\n"
                    "The entire assignment will be used."
                ))

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
        
        # Auto-update loaded template file if one is active
        self.update_loaded_template()

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
        total_sections = len(self.course_info)

        # Outcome name (pre-filled)
        name_input = QLineEdit()
        name_input.setText(old_name)
        name_input.setPlaceholderText("e.g., Critical Thinking")
        layout.addRow("Outcome Name:", name_input)
        
        # Threshold (pre-filled)

        
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
            dialog, item, name_input, assignment_list, old_name
        ))
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.exec()
    
    def update_outcome(self, dialog, list_item, name_input, assignment_list, old_name):
        """Update an existing outcome"""
        new_name = name_input.text().strip()
        
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
        outcome_text = new_name
        list_item.setText(outcome_text)
        
        list_item.setData(Qt.ItemDataRole.UserRole, {
            'name': new_name,
            'assignments': selected,
            'parts_config': parts_config
        })
        
        dialog.accept()
    
    def save_outcome(self, dialog, name_input, assignment_list):
        """Save the created outcome"""
        name = name_input.text().strip()
        
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
        outcome_text = name
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
            'assignments': selected,
            'parts_config': parts_config  # Store which parts to use
        })
        self.outcome_list.addItem(item)
        
        dialog.accept()
    
