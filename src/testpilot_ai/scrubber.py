"""TestPilot AI - Data scrubbing module."""

import re
from typing import Optional


class Scrubber:
    """Sensitive data scrubbing for test outputs."""
    
    # Patterns to detect and scrub
    PATTERNS = {
        "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "phone": r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        "ssn": r'\d{3}-\d{2}-\d{4}',
        "credit_card": r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
        "api_key": r'(?:sk|ghp|gho|github_pat)_[a-zA-Z0-9_]{20,}',
        "password": r'(?:password|passwd|pwd)\s*[:=]\s*\S+',
        "jwt": r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+',
    }
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._compiled_patterns = {}
        
        if enabled:
            for name, pattern in self.PATTERNS.items():
                self._compiled_patterns[name] = re.compile(pattern)
    
    def scrub(self, text: str) -> str:
        """Scrub sensitive data from text."""
        if not self.enabled:
            return text
        
        scrubbed = text
        
        for name, pattern in self._compiled_patterns.items():
            scrubbed = pattern.sub(f"[{name}_redacted]", scrubbed)
        
        return scrubbed
    
    def scrub_dict(self, data: dict) -> dict:
        """Recursively scrub sensitive data from nested dictionaries."""
        if not self.enabled:
            return data
        
        scrubbed = {}
        for key, value in data.items():
            if isinstance(value, str):
                scrubbed[key] = self.scrub(value)
            elif isinstance(value, dict):
                scrubbed[key] = self.scrub_dict(value)
            elif isinstance(value, list):
                scrubbed[key] = [
                    self.scrub_dict(item) if isinstance(item, dict) 
                    else self.scrub(item) if isinstance(item, str) 
                    else item
                    for item in value
                ]
            else:
                scrubbed[key] = value
        
        return scrubbed


# Module-level scrubber instance
scrubber = Scrubber()


def scrub_text(text: str) -> str:
    """Convenience function to scrub sensitive data."""
    return scrubber.scrub(text)


def scrub_result(result: dict) -> dict:
    """Convenience function to scrub test results."""
    return scrubber.scrub_dict(result)
