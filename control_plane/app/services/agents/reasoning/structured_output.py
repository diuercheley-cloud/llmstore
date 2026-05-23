# Owner: agent-platform
import logging
import json
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class StructuredOutputValidator:
    """
    Validates LLM output against a JSON schema or Pydantic model.
    """
    @staticmethod
    def parse_and_validate(content: str, schema: Optional[Dict[str, Any]] = None, model: Optional[Type[BaseModel]] = None) -> Dict[str, Any]:
        try:
            # Attempt to extract JSON if it's wrapped in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                 content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            if model:
                return model.model_validate(data).model_dump()
            
            # TODO: Add jsonschema validation if needed
            return data
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Structured output validation failed: {str(e)}")
            raise ValueError(f"Invalid structured output: {str(e)}")
