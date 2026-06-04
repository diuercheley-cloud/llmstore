import json
from typing import Tuple

import yaml


class ValidationService:
    @staticmethod
    def validate_manifest(content: str, file_type: str = "yaml") -> Tuple[bool, str]:
        """
        Validates the manifest format and required fields.
        """
        try:
            if file_type == "yaml":
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)
                
            if not data:
                return False, "Empty manifest"
                
            # Basic required fields for agents/plugins
            required = ["name", "version"]
            for field in required:
                if field not in data:
                    return False, f"Missing required field: {field}"
                    
            return True, "Valid manifest"
        except Exception as e:
            return False, f"Format error: {str(e)}"
