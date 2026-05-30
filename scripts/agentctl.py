import json
import yaml
import argparse
import os
import sys
import uuid
from pathlib import Path

class AgentCTL:
    def __init__(self):
        self.parser = argparse.ArgumentParser(prog="agentctl")
        subparsers = self.parser.add_subparsers(dest="command")

        # init
        init_parser = subparsers.add_parser("init")
        init_parser.add_argument("name")
        init_parser.add_argument("--template", default="support-triage")

        # validate
        validate_parser = subparsers.add_parser("validate")
        validate_parser.add_argument("path", nargs="?", default=".")

        # bundle
        bundle_parser = subparsers.add_parser("bundle")
        bundle_parser.add_argument("path", nargs="?", default=".")
        bundle_parser.add_argument("--output", "-o", default="agent-bundle.zip")

    def run(self):
        args = self.parser.parse_args()
        if not args.command:
            self.parser.print_help()
            return

        if args.command == "init":
            self.init(args.name, args.template)
        elif args.command == "validate":
            self.validate(args.path)
        elif args.command == "bundle":
            self.bundle(args.path, args.output)

    def init(self, name, template):
        print(f"Initializing agent '{name}' from template '{template}'...")
        # Simulating template copy
        os.makedirs(name, exist_ok=True)
        with open(os.path.join(name, "agent.yaml"), "w") as f:
            yaml.dump({
                "name": name,
                "version": "0.1.0",
                "description": f"Agent {name} initialized from {template}",
                "instructions": "You are a helpful agent.",
                "model_id": "gpt-4"
            }, f)
        print(f"Agent {name} created successfully.")

    def validate(self, path):
        yaml_path = os.path.join(path, "agent.yaml")
        if not os.path.exists(yaml_path):
            print(f"Error: agent.yaml not found in {path}")
            sys.exit(1)
        
        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
            
            required_fields = ["name", "version", "instructions", "model_id"]
            for field in required_fields:
                if field not in data:
                    print(f"Validation Error: Missing required field '{field}'")
                    sys.exit(1)
            
            print(f"Agent '{data['name']}' is valid.")
        except Exception as e:
            print(f"Validation Error: {e}")
            sys.exit(1)

    def bundle(self, path, output):
        print(f"Bundling agent in {path} to {output}...")
        # In a real tool, this would zip the directory
        with open(output, "w") as f:
            f.write("MOCK_BUNDLE_CONTENT")
        print("Bundle created successfully.")

if __name__ == "__main__":
    ctl = AgentCTL()
    ctl.run()
