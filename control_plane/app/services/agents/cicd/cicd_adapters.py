# Owner: agent-platform
import yaml
from typing import Dict, Any

class GitHubActionsAdapter:
    """
    Generates GitHub Actions workflow YAML for agent pipelines.
    """
    def generate_workflow(self, agent_id: str, tenant_id: str) -> str:
        workflow = {
            "name": f"Agent Deploy - {agent_id}",
            "on": {
                "push": {
                    "branches": ["main"],
                    "paths": [f"agents/{agent_id}/**"]
                }
            },
            "jobs": {
                "deploy": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {
                            "name": "Trigger Agent Pipeline",
                            "run": f"curl -X POST https://api.llm-stack.com/api/v1/admin/cicd/pipelines -d '{{\"agent_id\": \"{agent_id}\"}}'"
                        }
                    ]
                }
            }
        }
        return yaml.dump(workflow, sort_keys=False)

class JenkinsAdapter:
    """
    Minimal adapter for Jenkins integration.
    """
    def generate_pipeline_script(self, agent_id: str) -> str:
        return f"""
pipeline {{
    agent any
    stages {{
        stage('Deploy Agent') {{
            steps {{
                sh 'curl -X POST https://api.llm-stack.com/api/v1/admin/cicd/pipelines -d "{{\\"agent_id\\": \\"{agent_id}\\"}}"'
            }}
        }}
    }}
}}
"""
