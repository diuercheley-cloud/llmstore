# Owner: agent-platform
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

class TemplateGalleryService:
    """
    Manages reusable agent blueprints and templates for the Studio.
    """
    def __init__(self, templates_root: str = "examples/agents"):
        self.root = Path(templates_root)

    def list_templates(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all available templates with their metadata.
        """
        templates = []
        if not self.root.exists():
            logger.warning(f"Templates root {self.root} does not exist.")
            return []

        for agent_dir in self.root.iterdir():
            if agent_dir.is_dir():
                agent_yaml = agent_dir / "agent.yaml"
                if agent_yaml.exists():
                    try:
                        with open(agent_yaml, "r") as f:
                            data = yaml.safe_load(f)
                            data["template_id"] = agent_dir.name
                            templates.append(data)
                    except Exception as e:
                        logger.error(f"Error loading template {agent_dir.name}: {e}")
        
        return templates

    def get_template_details(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns full details for a specific template.
        """
        agent_dir = self.root / template_id
        agent_yaml = agent_dir / "agent.yaml"
        
        if not agent_yaml.exists():
            return None

        with open(agent_yaml, "r") as f:
            data = yaml.safe_load(f)
        
        # Load associated files
        for key, filename in [("instructions", "instructions.md"), ("readme", "README.md"), ("eval_suite", "eval_suite.json")]:
            file_path = agent_dir / filename
            if file_path.exists():
                with open(file_path, "r") as f:
                    if filename.endswith(".json"):
                        data[key] = json.load(f)
                    else:
                        data[key] = f.read()
        
        return data

    def validate_template(self, template_id: str) -> List[str]:
        """
        Validates that a template has all required files and correct structure.
        """
        errors = []
        agent_dir = self.root / template_id
        
        required_files = ["agent.yaml", "instructions.md", "eval_suite.json"]
        for f in required_files:
            if not (agent_dir / f).exists():
                errors.append(f"Missing required file: {f}")
        
        if not errors:
            # Validate YAML structure
            try:
                with open(agent_dir / "agent.yaml", "r") as f:
                    data = yaml.safe_load(f)
                    if "name" not in data or "model" not in data:
                        errors.append("agent.yaml missing 'name' or 'model' fields")
            except Exception as e:
                errors.append(f"Invalid YAML in agent.yaml: {e}")

        return errors
