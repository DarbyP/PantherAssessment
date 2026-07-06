"""
Panther Assessment - Configuration Utilities
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Application configuration manager"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"

        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file, fall back to minimal defaults"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return {
                'canvas': {'base_url': '', 'api_version': 'v1', 'request_timeout': 30},
                'ui': {'colors': {'primary': '#770000', 'secondary': '#CBCCCE'}},
                'templates': {'last_directory': ''},
                'output': {'timestamp_files': True},
            }

    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    @property
    def canvas_url(self) -> str:
        return self.get('canvas.base_url', '')

    @canvas_url.setter
    def canvas_url(self, value: str):
        self.set('canvas.base_url', value)

    @property
    def last_template_directory(self) -> str:
        return self.get('templates.last_directory', '')

    @last_template_directory.setter
    def last_template_directory(self, value: str):
        self.set('templates.last_directory', value)
        self.save()

    @property
    def primary_color(self) -> str:
        return self.get('ui.colors.primary', '#770000')

    @property
    def secondary_color(self) -> str:
        return self.get('ui.colors.secondary', '#CBCCCE')






_config = None

def get_config(config_path: Optional[Path] = None) -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
