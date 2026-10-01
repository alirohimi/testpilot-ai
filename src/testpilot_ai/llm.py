"""TestPilot AI - LLM integration for intelligent analysis."""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMConfig:
    """Configuration for LLM features."""

    api_key: str | None = None
    model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    temperature: float = 0.1

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")


class TestPilotLLM:
    """LLM-powered test analysis."""

    TRIAGE_PROMPT = """
You are a test failure analysis expert. Analyze the following test failure and provide:
1. Root cause classification
2. Suggested fix
3. Severity assessment

Test Failure:
{error_message}

Test Code:
{test_code}

Provide your analysis in JSON format:
{{
  "category": "<failure_category>",
  "root_cause": "<brief_description>",
  "suggested_fix": "<actionable_remediation>",
  "severity": "<critical|high|medium|low>",
  "confidence": <0.0-1.0>
}}
"""

    SCRUB_PROMPT = """
Identify and categorize sensitive data in the following test output.
Return a JSON array of findings with original value replaced by [REDACTED].

Output:
{output}
"""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = None

    def _get_client(self):
        """Lazy import and initialize OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.config.api_key)
            except ImportError:
                raise ImportError(
                    "OpenAI package required for LLM features. "
                    "Install with: pip install openai"
                )
        return self._client

    def analyze_failure(
        self,
        error_message: str,
        test_code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze a test failure using LLM."""
        if not self.config.api_key:
            return {
                "error": "No API key configured",
                "category": "unknown",
                "severity": "unknown",
            }

        try:
            client = self._get_client()

            prompt = self.TRIAGE_PROMPT.format(
                error_message=error_message[:2000], test_code=test_code or "N/A"
            )

            response = client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            content = response.choices[0].message.content

            # Parse JSON response
            import json

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "raw_response": content,
                    "category": "unknown",
                    "severity": "medium",
                }

        except Exception as e:
            return {"error": str(e), "category": "unknown", "severity": "unknown"}

    def is_available(self) -> bool:
        """Check if LLM features are available."""
        return bool(self.config.api_key)

    def get_status(self) -> dict[str, Any]:
        """Get LLM feature status."""
        return {
            "available": self.is_available(),
            "model": self.config.model,
            "has_api_key": bool(self.config.api_key),
        }


# Module-level instance
llm_analyzer = TestPilotLLM()


def get_llm_analyzer() -> TestPilotLLM:
    """Get the global LLM analyzer instance."""
    return llm_analyzer


def analyze_with_llm(error_message: str, **kwargs) -> dict[str, Any]:
    """Convenience function for LLM analysis."""
    return llm_analyzer.analyze_failure(error_message, **kwargs)
