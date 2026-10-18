"""
Resume tailoring with AI
Uses Claude/OpenAI to tailor resume per job
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ResumeTailor:
    """AI-powered resume tailoring"""

    def __init__(self, config: dict):
        self.config = config
        self.ai_config = config.get('ai', {})

        if self.ai_config.get('provider') == 'anthropic':
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.ai_config.get('anthropic_api_key'))
            self.model = self.ai_config.get('anthropic_model', 'claude-3-5-sonnet-20241022')
        elif self.ai_config.get('provider') == 'openai':
            from openai import OpenAI
            self.client = OpenAI(api_key=self.ai_config.get('openai_api_key'))
            self.model = self.ai_config.get('openai_model', 'gpt-4')
        else:
            self.client = None

    def tailor(self, job_title: str, job_description: str, resume_text: str) -> Optional[str]:
        """Tailor resume for a specific job"""

        if not self.client:
            logger.warning("No AI provider configured, returning original resume")
            return resume_text

        try:
            prompt = f"""You are a resume expert. Tailor the following resume to match this job posting.

Focus on:
1. Highlighting relevant skills and experience
2. Reordering bullet points to match job requirements
3. Using keywords from the job description
4. Keeping the same professional tone

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

ORIGINAL RESUME:
{resume_text}

Return ONLY the tailored resume text, no explanations."""

            if self.ai_config.get('provider') == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text

            elif self.ai_config.get('provider') == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Resume tailoring error: {e}")
            return resume_text

    def extract_keywords(self, job_description: str) -> list:
        """Extract keywords from job description"""

        if not self.client:
            return []

        try:
            prompt = f"""Extract the top 10 technical skills and keywords from this job description.
Return as a simple comma-separated list.

JOB DESCRIPTION:
{job_description}"""

            if self.ai_config.get('provider') == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=200,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                text = message.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200
                )
                text = response.choices[0].message.content

            return [k.strip() for k in text.split(',')]

        except Exception as e:
            logger.error(f"Keyword extraction error: {e}")
            return []
