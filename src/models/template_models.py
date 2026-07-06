"""
Canvas Multi-Section Assessment Data Reporter - Configuration Template Models
Data structures for saving and loading report configurations
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional
import json
from pathlib import Path


@dataclass
class TemplateQuestionGroup:
    """Question group configuration in a template"""
    name: str
    selected: bool = True


@dataclass
class TemplateRubricCriterion:
    """Rubric criterion configuration in a template"""
    description: str
    selected: bool = True


@dataclass
class TemplateAssignment:
    """Assignment configuration in a template"""
    name: str
    assignment_type: str
    included: bool = True
    weight: float = 1.0
    question_groups: List[TemplateQuestionGroup] = field(default_factory=list)
    rubric_criteria: List[TemplateRubricCriterion] = field(default_factory=list)


@dataclass
class TemplateOutcome:
    """Outcome configuration in a template"""
    title: str
    description: str
    threshold: float = 70.0
    included: bool = True
    assignments: List[TemplateAssignment] = field(default_factory=list)


@dataclass
class CourseTemplate:
    """Complete course configuration template"""
    template_name: str
    course_code: str
    created_date: datetime
    last_modified: datetime
    created_by: str
    outcomes: List[TemplateOutcome] = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> Dict:
        """Convert template to dictionary for JSON serialization"""
        data = asdict(self)
        data['created_date'] = self.created_date.isoformat()
        data['last_modified'] = self.last_modified.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CourseTemplate':
        """Create template from dictionary"""
        data['created_date'] = datetime.fromisoformat(data['created_date'])
        data['last_modified'] = datetime.fromisoformat(data['last_modified'])
        
        # Reconstruct nested objects
        outcomes = []
        for outcome_data in data.get('outcomes', []):
            assignments = []
            for assignment_data in outcome_data.get('assignments', []):
                question_groups = [
                    TemplateQuestionGroup(**qg) 
                    for qg in assignment_data.get('question_groups', [])
                ]
                rubric_criteria = [
                    TemplateRubricCriterion(**rc) 
                    for rc in assignment_data.get('rubric_criteria', [])
                ]
                assignment = TemplateAssignment(
                    name=assignment_data['name'],
                    assignment_type=assignment_data['assignment_type'],
                    included=assignment_data.get('included', True),
                    weight=assignment_data.get('weight', 1.0),
                    question_groups=question_groups,
                    rubric_criteria=rubric_criteria
                )
                assignments.append(assignment)
            
            outcome = TemplateOutcome(
                title=outcome_data['title'],
                description=outcome_data['description'],
                threshold=outcome_data.get('threshold', 70.0),
                included=outcome_data.get('included', True),
                assignments=assignments
            )
            outcomes.append(outcome)
        
        return cls(
            template_name=data['template_name'],
            course_code=data['course_code'],
            created_date=data['created_date'],
            last_modified=data['last_modified'],
            created_by=data.get('created_by', 'Unknown'),
            outcomes=outcomes,
            notes=data.get('notes', '')
        )
    
    def save(self, directory: Path) -> Path:
        """Save template to JSON file"""
        directory.mkdir(parents=True, exist_ok=True)
        
        # Create filename from course code and template name
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' 
                           for c in self.template_name)
        filename = f"{self.course_code}_{safe_name}.json"
        filepath = directory / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        return filepath
    
    @classmethod
    def load(cls, filepath: Path) -> 'CourseTemplate':
        """Load template from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def __str__(self):
        return f"{self.template_name} ({self.course_code}) - {len(self.outcomes)} outcomes"


class TemplateManager:
    """Manages configuration templates"""
    
    def __init__(self, template_directory: Path):
        self.template_directory = Path(template_directory)
        self.template_directory.mkdir(parents=True, exist_ok=True)
    
    def list_templates(self, course_code: Optional[str] = None) -> List[CourseTemplate]:
        """List all available templates, optionally filtered by course code"""
        templates = []
        
        for filepath in self.template_directory.glob("*.json"):
            try:
                template = CourseTemplate.load(filepath)
                if course_code is None or template.course_code == course_code:
                    templates.append(template)
            except Exception as e:
                print(f"Warning: Could not load template {filepath}: {e}")
        
        # Sort by course code, then by last modified date
        templates.sort(key=lambda t: (t.course_code, t.last_modified), reverse=True)
        return templates
    
    def get_template(self, course_code: str, template_name: str) -> Optional[CourseTemplate]:
        """Get a specific template by course code and name"""
        templates = self.list_templates(course_code)
        for template in templates:
            if template.template_name == template_name:
                return template
        return None
    
    def save_template(self, template: CourseTemplate) -> Path:
        """Save a template"""
        template.last_modified = datetime.now()
        return template.save(self.template_directory)
    
    def delete_template(self, course_code: str, template_name: str) -> bool:
        """Delete a template"""
        template = self.get_template(course_code, template_name)
        if template:
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' 
                               for c in template_name)
            filename = f"{course_code}_{safe_name}.json"
            filepath = self.template_directory / filename
            
            if filepath.exists():
                filepath.unlink()
                return True
        return False
    
    def export_template(self, template: CourseTemplate, export_path: Path) -> Path:
        """Export a template to a specific location"""
        return template.save(export_path.parent)
    
    def import_template(self, import_path: Path) -> CourseTemplate:
        """Import a template from a file"""
        template = CourseTemplate.load(import_path)
        # Save to template directory
        self.save_template(template)
        return template
