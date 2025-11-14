"""
Canvas Multi-Section Assessment Data Reporter - Canvas API Client
Handles all communication with Canvas LMS API
"""

import requests
from typing import List, Dict, Optional, Any
import time
from datetime import datetime
import keyring


class CanvasAPIError(Exception):
    """Custom exception for Canvas API errors"""
    pass


class CanvasAPIClient:
    """Client for Canvas LMS API"""
    
    def __init__(self, base_url: str, api_token: Optional[str] = None, timeout: int = 30):
        """
        Initialize Canvas API client
        
        Args:
            base_url: Canvas instance URL (e.g., "https://canvas.university.edu")
            api_token: Canvas API token (if None, will attempt to load from keyring)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set API token
        if api_token:
            self.api_token = api_token
        else:
            # Try to load from keyring
            self.api_token = self._load_token_from_keyring()
        
        if self.api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            })
    
    def _load_token_from_keyring(self) -> Optional[str]:
        """Load API token from system keyring"""
        try:
            return keyring.get_password("pantherassess", "api_token")
        except Exception:
            return None
    
    def save_token_to_keyring(self, token: str):
        """Save API token to system keyring"""
        try:
            keyring.set_password("pantherassess", "api_token", token)
            self.api_token = token
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            })
        except Exception as e:
            raise CanvasAPIError(f"Failed to save token: {e}")
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Any:
        """
        Make a request to Canvas API with error handling and rate limiting
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/v1/courses")
            params: Query parameters
            data: Request body data
            
        Returns:
            Response data (JSON)
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self.timeout
            )
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
                return self._make_request(method, endpoint, params, data)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise CanvasAPIError("Invalid API token or expired session")
            elif e.response.status_code == 403:
                raise CanvasAPIError("Insufficient permissions to access this resource")
            elif e.response.status_code == 404:
                raise CanvasAPIError("Resource not found")
            else:
                raise CanvasAPIError(f"HTTP Error: {e}")
        except requests.exceptions.Timeout:
            raise CanvasAPIError("Request timed out")
        except requests.exceptions.ConnectionError:
            raise CanvasAPIError("Connection error - check your internet connection")
        except Exception as e:
            raise CanvasAPIError(f"Unexpected error: {e}")
    
    def _paginate(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Handle pagination for Canvas API requests
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            List of all results across all pages
        """
        if params is None:
            params = {}
        
        params['per_page'] = 100  # Max allowed by Canvas
        
        all_results = []
        url = f"{self.base_url}{endpoint}"
        
        while url:
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                results = response.json()
                
                if isinstance(results, list):
                    all_results.extend(results)
                else:
                    all_results.append(results)
                
                # Check for next page
                links = response.headers.get('Link', '')
                next_url = None
                for link in links.split(','):
                    if 'rel="next"' in link:
                        next_url = link.split(';')[0].strip('<> ')
                        break
                
                url = next_url
                params = None  # URL already includes params
                
            except requests.exceptions.RequestException as e:
                raise CanvasAPIError(f"Pagination error: {e}")
        
        return all_results
    
    def test_connection(self) -> bool:
        """Test API connection and token validity"""
        try:
            self._make_request('GET', '/api/v1/users/self')
            return True
        except CanvasAPIError:
            return False
    
    def get_user_info(self) -> Dict:
        """Get current user information"""
        return self._make_request('GET', '/api/v1/users/self')
    
    def get_courses(self, enrollment_type: Optional[str] = None) -> List[Dict]:
        """
        Get courses for the current user
        
        Args:
            enrollment_type: Filter by enrollment type (teacher, ta, student, etc.)
            
        Returns:
            List of course dictionaries
        """
        params = {
            'include[]': ['term', 'total_students'],
            'enrollment_state': 'active'
        }
        
        if enrollment_type:
            params['enrollment_type'] = enrollment_type
        
        return self._paginate('/api/v1/courses', params)
    
    def get_course(self, course_id: str) -> Dict:
        """Get details for a specific course"""
        params = {'include[]': ['term', 'total_students']}
        return self._make_request('GET', f'/api/v1/courses/{course_id}', params)
    
    def get_enrollments(self, course_id: str) -> List[Dict]:
        """Get student enrollments for a course"""
        params = {
            'type[]': 'StudentEnrollment',
            'state[]': 'active'
        }
        return self._paginate(f'/api/v1/courses/{course_id}/enrollments', params)
    
    def get_outcomes(self, course_id: str) -> List[Dict]:
        """Get learning outcomes for a course"""
        outcome_links = self._paginate(
            f'/api/v1/courses/{course_id}/outcome_group_links'
        )
        
        outcomes = []
        for link in outcome_links:
            if 'outcome' in link and 'id' in link['outcome']:
                outcome_id = link['outcome']['id']
                outcome = self._make_request('GET', f'/api/v1/outcomes/{outcome_id}')
                outcomes.append(outcome)
        
        return outcomes
    
    def get_assignments(self, course_id: str) -> List[Dict]:
        """Get assignments for a course"""
        params = {'include[]': ['rubric', 'submission']}
        return self._paginate(f'/api/v1/courses/{course_id}/assignments', params)
    
    def get_assignment(self, course_id: str, assignment_id: str) -> Dict:
        """Get details for a specific assignment"""
        params = {'include[]': ['rubric', 'submission']}
        return self._make_request(
            'GET', 
            f'/api/v1/courses/{course_id}/assignments/{assignment_id}',
            params
        )
    
    def get_quiz(self, course_id: str, quiz_id: str) -> Dict:
        """Get quiz details"""
        return self._make_request('GET', f'/api/v1/courses/{course_id}/quizzes/{quiz_id}')
    
    def get_quiz_questions(self, course_id: str, quiz_id: str) -> List[Dict]:
        """Get questions for a quiz"""
        return self._paginate(f'/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions')
    
    def get_submissions(self, course_id: str, assignment_id: str) -> List[Dict]:
        """Get submissions for an assignment"""
        params = {
            'include[]': ['rubric_assessment', 'submission_history'],
            'per_page': 100
        }
        return self._paginate(
            f'/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions',
            params
        )
    
    def get_quiz_submissions(self, course_id: str, quiz_id: str) -> List[Dict]:
        """Get submissions for a quiz"""
        params = {'include[]': ['submission', 'quiz']}
        return self._paginate(
            f'/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions',
            params
        )
