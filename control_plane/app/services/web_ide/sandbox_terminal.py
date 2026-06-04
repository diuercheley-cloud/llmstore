import logging
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)

class SandboxTerminal:
    @staticmethod
    async def run_command(command: str, cwd: str) -> Dict[str, Any]:
        """
        Runs a command in a restricted way.
        Currently only allowing specific commands like 'pytest' or 'ls'.
        """
        allowed_commands = ["pytest", "ls", "cat"]
        base_cmd = command.split()[0]
        
        if base_cmd not in allowed_commands:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Command '{base_cmd}' is not allowed in the sandbox."
            }

        try:
            # In a real system, this would run inside a Docker container or Firecracker VM
            process = subprocess.Popen(
                command,
                shell=False, # Secure
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=30)
            return {
                "exit_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr
            }
        except subprocess.TimeoutExpired:
            process.kill()
            return {"exit_code": 124, "stdout": "", "stderr": "Command timed out"}
        except Exception as e:
            return {"exit_code": 1, "stdout": "", "stderr": str(e)}
