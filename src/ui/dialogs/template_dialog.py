"""
Panther Assessment - Template Dialog Mixin
Template open/save using standard file dialogs.
Templates are portable .json files stored wherever the user chooses.
"""

import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QFileDialog, QLineEdit, QFormLayout
)
from PyQt6.QtCore import Qt


class TemplateDialogMixin:
    """Mixin providing template open/save for MainWindow"""

    # ── Migration notice ─────────────────────────────────────────────────────

    def check_template_migration(self):
        """
        On first launch after upgrade, notify user about old hidden template folder.
        Only shown once — stored in config.
        """
        if self.config.get('templates.migration_shown', False):
            return

        try:
            from src.utils.resources import get_user_templates_dir
            old_dir = get_user_templates_dir()
            old_templates = list(old_dir.glob('*.json')) if old_dir.exists() else []
        except Exception:
            old_templates = []
            old_dir = None

        if old_templates:
            from PyQt6.QtWidgets import QCheckBox
            dialog = QDialog(self)
            dialog.setWindowTitle("Template Storage Has Changed")
            layout = QVBoxLayout(dialog)

            msg = QLabel(
                f"Panther Assessment now lets you save templates anywhere you choose.\n\n"
                f"Your {len(old_templates)} previous template(s) are stored in a system folder. "
                f"Would you like to open that folder so you can move them to your preferred locations?"
            )
            msg.setWordWrap(True)
            layout.addWidget(msg)

            dont_show = QCheckBox("Do not show this again")
            layout.addWidget(dont_show)

            btn_layout = QHBoxLayout()
            yes_btn = QPushButton("Yes, Open Folder")
            no_btn = QPushButton("No")
            btn_layout.addWidget(yes_btn)
            btn_layout.addWidget(no_btn)
            layout.addLayout(btn_layout)

            yes_btn.clicked.connect(dialog.accept)
            no_btn.clicked.connect(dialog.reject)

            result = dialog.exec()

            if dont_show.isChecked():
                self.config.set('templates.migration_shown', True)
                self.config.save()

            if result == QDialog.DialogCode.Accepted:
                import subprocess, platform
                if platform.system() == 'Windows':
                    subprocess.run(['explorer', str(old_dir)])
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', str(old_dir)])
                else:
                    subprocess.run(['xdg-open', str(old_dir)])

    # ── Save template ────────────────────────────────────────────────────────

    def save_as_template(self, *args):
        """Save current outcomes as a template .json file"""
        if not hasattr(self, 'outcome_list') or self.outcome_list.count() == 0:
            QMessageBox.warning(self, "No Outcomes", "Please add at least one outcome before saving a template.")
            return

        # Build template name suggestion from course info
        course_suffix = ''
        if self.course_info:
            names = list({c.get('name', '').split(',')[0].strip() for c in self.course_info})
            course_suffix = '_' + '_'.join(names)[:40] if names else ''

        default_name = f"template{course_suffix}.json"
        last_dir = self.config.last_template_directory
        default_path = str(Path(last_dir) / default_name) if last_dir else str(Path.home() / "Desktop" / default_name)

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Template",
            default_path,
            "Template Files (*.json)"
        )

        if not filepath:
            return

        filepath = Path(filepath)
        self.config.last_template_directory = str(filepath.parent)

        # Collect outcomes from list
        outcomes = []
        for i in range(self.outcome_list.count()):
            item = self.outcome_list.item(i)
            outcomes.append(item.data(Qt.ItemDataRole.UserRole))

        template_data = {
            'name': filepath.stem,
            'saved_at': datetime.now().isoformat(),
            'outcomes': outcomes
        }

        try:
            with open(filepath, 'w') as f:
                json.dump(template_data, f, indent=2)
            self._loaded_template_filepath = filepath
            self._loaded_template_name = filepath.stem
            QMessageBox.information(self, "Template Saved", f"Template saved to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save template:\n{str(e)}")

    # ── Load template ────────────────────────────────────────────────────────

    def load_template_dialog(self):
        """Open a template .json file"""
        if not hasattr(self, 'all_assignments') or not self.all_assignments:
            QMessageBox.warning(self, "No Course Selected",
                "Please select a course and click Continue before loading a template.")
            return

        last_dir = self.config.last_template_directory
        start_dir = last_dir if last_dir else str(Path.home() / "Desktop")

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Template",
            start_dir,
            "Template Files (*.json)"
        )

        if not filepath:
            return

        filepath = Path(filepath)
        self.config.last_template_directory = str(filepath.parent)

        try:
            with open(filepath, 'r') as f:
                template_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Could not read template file:\n{str(e)}")
            return

        outcomes = template_data.get('outcomes', [])
        if not outcomes:
            QMessageBox.warning(self, "Empty Template", "This template has no outcomes.")
            return

        # Confirm if outcomes already exist
        if self.outcome_list.count() > 0:
            reply = QMessageBox.question(
                self, "Replace Outcomes?",
                "Loading this template will replace your current outcomes. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.outcome_list.clear()
        self._loaded_template_filepath = filepath
        self._loaded_template_name = filepath.stem

        # Match template outcomes to current course assignments
        self._apply_template_outcomes(outcomes)

    def _apply_template_outcomes(self, outcomes):
        """Match template outcomes to current loaded assignments and populate outcome list"""
        from PyQt6.QtWidgets import QListWidgetItem

        unmatched = []

        for outcome_data in outcomes:
            outcome_name = outcome_data.get('name', outcome_data.get('title', 'Unnamed'))
            old_parts_config = outcome_data.get('parts_config', {})
            assignments = outcome_data.get('assignments', [])

            matched_assignments = []
            new_parts_config = {}

            for assignment in assignments:
                assignment_name = assignment.get('name', '')
                old_assignment_id = assignment.get('id')

                # Match by name to current course assignments
                matched = next(
                    (a for a in self.all_assignments
                     if a.get('name', '').strip().lower() == assignment_name.strip().lower()),
                    None
                )

                if not matched:
                    unmatched.append(assignment_name)
                    continue

                new_assignment_id = matched.get('id')
                parts_key = str(old_assignment_id) if str(old_assignment_id) in old_parts_config \
                    else old_assignment_id
                old_parts = old_parts_config.get(parts_key) or old_parts_config.get(str(parts_key))

                if not old_parts or not isinstance(old_parts, list):
                    matched_assignments.append(matched)
                    continue

                # Re-map parts to new course IDs
                new_parts = []
                course_ids = matched.get('course_ids', [matched.get('course_id')])
                assignment_ids_by_course = matched.get('assignment_ids_by_course', {})
                quiz_ids_by_course = matched.get('quiz_ids_by_course', {})

                for part in old_parts:
                    if not isinstance(part, dict):
                        continue
                    part_type = part.get('type')

                    if part_type == 'quiz_group':
                        group_name = part.get('group_name', '')
                        new_group_ids = {}
                        new_pick_counts = {}
                        new_question_points = {}

                        for course_id in course_ids:
                            course_quiz_id = quiz_ids_by_course.get(course_id)
                            if not course_quiz_id:
                                continue
                            try:
                                groups = self.canvas_client.get_quiz_groups(course_id, course_quiz_id)
                                for group in groups:
                                    if group.get('name', '').strip().lower() == group_name.strip().lower():
                                        new_group_ids[str(course_id)] = group.get('id')
                                        new_pick_counts[str(course_id)] = group.get('pick_count', 0)
                                        new_question_points[str(course_id)] = group.get('question_points', 0)
                                        break
                            except Exception:
                                pass

                        if new_group_ids:
                            new_parts.append({
                                'type': 'quiz_group',
                                'group_name': group_name,
                                'group_ids_by_course': new_group_ids,
                                'pick_count_by_course': new_pick_counts,
                                'question_points_by_course': new_question_points,
                                'assignment_id': new_assignment_id
                            })

                    elif part_type == 'rubric_criterion':
                        description = part.get('description', '')
                        criterion_points = part.get('points', 0)
                        new_criterion_ids = {}

                        for course_id in course_ids:
                            course_assignment_id = assignment_ids_by_course.get(course_id, new_assignment_id)
                            try:
                                assignment_detail = self.canvas_client.get_assignment(course_id, course_assignment_id)
                                rubric = assignment_detail.get('rubric', [])
                                for criterion in rubric:
                                    if criterion.get('description', '').strip().lower() == description.strip().lower():
                                        new_criterion_ids[str(course_id)] = criterion.get('id')
                                        criterion_points = criterion.get('points', criterion_points)
                                        break
                            except Exception:
                                pass

                        if new_criterion_ids:
                            new_parts.append({
                                'type': 'rubric_criterion',
                                'description': description,
                                'criterion_ids_by_course': new_criterion_ids,
                                'points': criterion_points,
                                'assignment_id': new_assignment_id
                            })

                if new_parts:
                    new_parts_config[new_assignment_id] = new_parts
                matched_assignments.append(matched)

            if matched_assignments:
                item = QListWidgetItem(outcome_name)
                item.setData(Qt.ItemDataRole.UserRole, {
                    'name': outcome_name,
                    'assignments': matched_assignments,
                    'parts_config': new_parts_config
                })
                self.outcome_list.addItem(item)

        if unmatched:
            QMessageBox.information(
                self, "Some Assignments Not Found",
                f"The following assignments from the template were not found in this course:\n\n"
                + "\n".join(f"• {a}" for a in unmatched)
                + "\n\nAll other outcomes have been loaded."
            )

    # ── Update loaded template ───────────────────────────────────────────────

    def update_loaded_template(self):
        """Save current outcomes back to the loaded template file"""
        loaded_filepath = getattr(self, '_loaded_template_filepath', None)
        loaded_name = getattr(self, '_loaded_template_name', None)
        if not loaded_filepath or not Path(loaded_filepath).exists():
            return
        try:
            outcomes = []
            for i in range(self.outcome_list.count()):
                item = self.outcome_list.item(i)
                outcomes.append(item.data(Qt.ItemDataRole.UserRole))
            template_data = {
                'name': loaded_name,
                'saved_at': datetime.now().isoformat(),
                'outcomes': outcomes
            }
            with open(loaded_filepath, 'w') as f:
                json.dump(template_data, f, indent=2)
        except Exception:
            pass  # Silent — don't block the user
