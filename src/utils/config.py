"""
Canvas Multi-Section Assessment Data Reporter - Configuration Utilities
Load and manage application configuration
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Application configuration manager"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config.yaml file
        """
        if config_path is None:
            # Default to config.yaml in project root
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Return default configuration
            return self._default_config()
        except Exception as e:
            print(f"Warning: Error loading config: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'canvas': {
                'base_url': '',
                'api_version': 'v1',
                'request_timeout': 30
            },
            'ui': {
                'colors': {
                    'primary': '#770000',
                    'secondary': '#CBCCCE',
                    'background': '#FFFFFF',
                    'text': '#000000',
                    'success': '#2E7D32',
                    'warning': '#F57C00',
                    'error': '#C62828'
                }
            },
            'report_settings': {
                'default_threshold': 70,
                'borderline_range': 5,
                'excel_colors': {
                    'met': '90EE90',
                    'not_met': 'FFB6C1',
                    'borderline': 'FFFFE0'
                }
            },
            'aggregation': {
                'include_withdrawn': False,
                'minimum_submission_rate': 0.5
            },
            'output': {
                'default_directory': './reports',
                'timestamp_files': True,
                'include_raw_data_sheet': True,
                'csv_export': True
            },
            'templates': {
                'storage_directory': './templates',
                'auto_suggest': True,
                'allow_export': True,
                'allow_import': True
            },
            'user_settings': {
                'save_preferences': True,
                'share_configurations': False,
                'remember_last_course': True
            }
        }
    
    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path (e.g., 'canvas.base_url')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key_path: Dot-separated path (e.g., 'canvas.base_url')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config
        
        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
    
    @property
    def canvas_url(self) -> str:
        """Get Canvas base URL"""
        return self.get('canvas.base_url', '')
    
    @canvas_url.setter
    def canvas_url(self, value: str):
        """Set Canvas base URL"""
        self.set('canvas.base_url', value)
    
    @property
    def primary_color(self) -> str:
        """Get primary UI color (university maroon)"""
        return self.get('ui.colors.primary', '#770000')
    
    @property
    def secondary_color(self) -> str:
        """Get secondary UI color (university gray)"""
        return self.get('ui.colors.secondary', '#CBCCCE')
    
    @property
    def template_directory(self) -> Path:
        """Get template storage directory"""
        dir_path = self.get('templates.storage_directory', './templates')
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def report_directory(self) -> Path:
        """Get report output directory"""
        dir_path = self.get('output.default_directory', './reports')
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def default_threshold(self) -> float:
        """Get default mastery threshold"""
        return float(self.get('report_settings.default_threshold', 70))


# Global configuration instance
_config = None

def get_config(config_path: Optional[Path] = None) -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
