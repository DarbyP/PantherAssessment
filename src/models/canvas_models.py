"""
Canvas Multi-Section Assessment Data Reporter - Data Models
Core data structures for Canvas objects
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class AssignmentType(Enum):
    """Types of Canvas assignments"""
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    DISCUSSION = "discussion"
    EXTERNAL_TOOL = "external_tool"


@dataclass
class CourseSection:
    """Represents a Canvas course section"""
    id: str
    name: str
    course_code: str
    section_number: str
    term: str
    enrollment_count: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    instructor: str
    
    def __str__(self):
        return f"{self.course_code}-{self.section_number} ({self.term}) - {self.enrollment_count} students"


@dataclass
class Outcome:
    """Represents a learning outcome"""
    id: str
    title: str
    description: str
    threshold: float = 70.0  # Default mastery threshold
    included: bool = True
    
    def __str__(self):
        return f"{self.title} (Threshold: {self.threshold}%)"


@dataclass
class QuestionGroup:
    """Represents a question group within a quiz"""
    id: str
    name: str
    points_possible: float
    question_count: int
    selected: bool = True


@dataclass
class RubricCriterion:
    """Represents a rubric criterion"""
    id: str
    description: str
    points: float
    selected: bool = True


@dataclass
class Assignment:
    """Represents a Canvas assignment"""
    id: str
    name: str
    assignment_type: AssignmentType
    points_possible: float
    outcome_id: Optional[str] = None
    
    # For quizzes
    question_groups: List[QuestionGroup] = field(default_factory=list)
    
    # For rubric-graded assignments
    rubric_criteria: List[RubricCriterion] = field(default_factory=list)
    
    # Selection state
    included: bool = True
    weight: float = 1.0
    
    def get_selected_points(self) -> float:
        """Calculate total points from selected components"""
        if self.assignment_type == AssignmentType.QUIZ:
            return sum(qg.points_possible for qg in self.question_groups if qg.selected)
        elif self.rubric_criteria:
            return sum(rc.points for rc in self.rubric_criteria if rc.selected)
        return self.points_possible if self.included else 0.0
    
    def __str__(self):
        return f"{self.name} ({self.assignment_type.value}) - {self.points_possible} pts"


@dataclass
class OutcomeAssignment:
    """Links an outcome to its contributing assignments"""
    outcome: Outcome
    assignments: List[Assignment] = field(default_factory=list)
    
    def get_total_points(self) -> float:
        """Calculate total possible points for this outcome"""
        return sum(a.get_selected_points() * a.weight for a in self.assignments if a.included)


@dataclass
class StudentScore:
    """Represents a student's score for an assignment component"""
    student_id: str
    assignment_id: str
    component_id: Optional[str] = None  # Question group or rubric criterion ID
    points_earned: float = 0.0
    points_possible: float = 0.0
    
    def get_percentage(self) -> float:
        """Calculate percentage score"""
        if self.points_possible == 0:
            return 0.0
        return (self.points_earned / self.points_possible) * 100


@dataclass
class StudentOutcomeScore:
    """Represents a student's aggregated score for an outcome"""
    student_id: str
    student_name: str
    section_id: str
    outcome_id: str
    points_earned: float
    points_possible: float
    component_scores: List[StudentScore] = field(default_factory=list)
    
    def get_percentage(self) -> float:
        """Calculate percentage score for the outcome"""
        if self.points_possible == 0:
            return 0.0
        return (self.points_earned / self.points_possible) * 100
    
    def meets_threshold(self, threshold: float) -> bool:
        """Check if student meets the mastery threshold"""
        return self.get_percentage() >= threshold


@dataclass
class Student:
    """Represents a student enrollment"""
    id: str
    name: str
    sortable_name: str
    section_id: str
    enrollment_state: str = "active"
    
    def __str__(self):
        return self.sortable_name


@dataclass
class AggregatedData:
    """Aggregated data across all sections for reporting"""
    course_code: str
    term: str
    sections: List[CourseSection]
    outcomes: List[Outcome]
    students: List[Student]
    student_scores: Dict[str, Dict[str, StudentOutcomeScore]]  # student_id -> outcome_id -> score
    
    def get_total_enrollment(self) -> int:
        """Get total student count across all sections"""
        return len(self.students)
    
    def get_outcome_statistics(self, outcome_id: str) -> Dict:
        """Calculate statistics for a specific outcome"""
        scores = []
        met_count = 0
        outcome = next((o for o in self.outcomes if o.id == outcome_id), None)
        
        if not outcome:
            return {}
        
        for student_id, outcome_scores in self.student_scores.items():
            if outcome_id in outcome_scores:
                score = outcome_scores[outcome_id]
                percentage = score.get_percentage()
                scores.append(percentage)
                if score.meets_threshold(outcome.threshold):
                    met_count += 1
        
        if not scores:
            return {
                'outcome': outcome,
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'std_dev': 0.0,
                'percent_meeting': 0.0
            }
        
        import statistics
        return {
            'outcome': outcome,
            'count': len(scores),
            'mean': statistics.mean(scores),
            'median': statistics.median(scores),
            'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0.0,
            'percent_meeting': (met_count / len(scores)) * 100
        }
