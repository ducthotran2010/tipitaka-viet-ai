import yaml
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

class TemplateLoader:
    _instance = None
    _templates = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TemplateLoader, cls).__new__(cls)
            cls._instance._load_templates()
        return cls._instance
    
    def _load_templates(self):
        """Load all templates from YAML file"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_path = os.path.join(base_dir, 'templates', 'prompts.yaml')
            
            with open(template_path, 'r', encoding='utf-8') as file:
                self._templates = yaml.safe_load(file)
                logger.info(f"Successfully loaded templates from {template_path}")
        except Exception as e:
            logger.error(f"Failed to load templates: {str(e)}")
            # Provide minimal default templates in case of failure
            self._templates = {
                "messages": {
                    "health_check_failed": "Kính thưa thiện hữu, vui lòng thử lại trong giây lát."
                }
            }
    
    def get_introduction_messages(self) -> List[str]:
        """Get list of introduction messages"""
        return self._templates.get('introduction_messages', [])
    
    def get_system_prompt(self) -> str:
        """Get system prompt template"""
        return self._templates.get('system_prompt', '')
    
    def get_source_template(self) -> str:
        """Get source template"""
        return self._templates.get('source_template', '')
    
    def get_quote_template(self) -> str:
        """Get quote template"""
        return self._templates.get('quote_template', '')
    
    def get_message(self, key: str) -> str:
        """Get a specific message by key"""
        return self._templates.get('messages', {}).get(key, '')
    
    def get_search_keyword_template(self) -> str:
        """Get search keyword template"""
        return self._templates.get('search_keyword_template', '')
    
    def get_response_template(self) -> str:
        """Get response template"""
        return self._templates.get('response_template', '')
    
    def get_response_template_with_quote(self) -> str:
        """Get response template with quote"""
        return self._templates.get('response_template_with_quote', '')
    
    def get_bot_summary_template(self) -> str:
        """Get bot summary template"""
        return self._templates.get('bot_summary_template', '')
    
    def reload_templates(self):
        """Force reload templates from file"""
        self._load_templates()
        return self._templates is not None
