import os
import unittest

import yaml

from scripts.agentctl import AgentCTL


class TestAgentManifest(unittest.TestCase):
    def setUp(self):
        self.ctl = AgentCTL()
        self.test_dir = "test_agent_dir"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_valid_manifest_passes(self):
        manifest = {
            "name": "test-agent",
            "version": "1.0.0",
            "model": "mock",
            "instructions_file": "instructions.md"
        }
        with open(os.path.join(self.test_dir, "agent.yaml"), "w") as f:
            yaml.dump(manifest, f)
        
        # Should not raise SystemExit
        self.ctl.validate(self.test_dir)

    def test_manifest_with_secret_fails(self):
        manifest = {
            "name": "test-agent",
            "version": "1.0.0",
            "model": "mock",
            "instructions_file": "instructions.md",
            "api_key": "sk-1234567890"
        }
        with open(os.path.join(self.test_dir, "agent.yaml"), "w") as f:
            yaml.dump(manifest, f)
        
        with self.assertRaises(SystemExit):
            self.ctl.validate(self.test_dir)

if __name__ == "__main__":
    unittest.main()
