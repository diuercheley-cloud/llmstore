#!/usr/bin/env python3
import os
import sys
import yaml
import json
import argparse
import requests

class AgentCTL:
    def __init__(self):
        self.api_key = os.environ.get("KLEBER_API_KEY")
        self.base_url = os.environ.get("KLEBER_BASE_URL", "http://localhost:18080")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def init(self, name, template):
        print(f"Initializing agent '{name}' from template '{template}'...")
        os.makedirs(name, exist_ok=True)
        manifest = {
            "name": name,
            "version": "0.1.0",
            "description": f"Agent {name} generated from template {template}",
            "instructions_file": "instructions.md",
            "model": "gpt-4o",
            "tools": [],
            "memory_policy": {"enabled": True},
            "eval_suite": "standard",
            "risk_level": "low",
            "owner": os.environ.get("USER", "developer"),
            "environment": "dev",
            "supported_surface_status": "draft"
        }
        with open(os.path.join(name, "agent.yaml"), "w") as f:
            yaml.dump(manifest, f)
        with open(os.path.join(name, "instructions.md"), "w") as f:
            f.write(f"# Instructions for {name}\n\nYou are a helpful agent...")
        print(f"Agent '{name}' initialized in directory '{name}'.")

    def validate(self, path):
        print(f"Validating manifest at {path}...")
        manifest_path = os.path.join(path, "agent.yaml")
        if not os.path.exists(manifest_path):
            print(f"Error: {manifest_path} not found.")
            sys.exit(1)
        
        with open(manifest_path, "r") as f:
            try:
                manifest = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"Error parsing YAML: {e}")
                sys.exit(1)

        # Check for secrets (simple mock check)
        manifest_str = json.dumps(manifest)
        if "sk-" in manifest_str or "AIza" in manifest_str:
            print("Error: Potential secret detected in manifest.")
            sys.exit(1)

        # Check required fields
        required = ["name", "version", "model", "instructions_file"]
        for field in required:
            if field not in manifest:
                print(f"Error: Missing required field '{field}'.")
                sys.exit(1)

        print("Manifest is valid.")

    def register(self, path):
        self.validate(path)
        print(f"Registering agent from {path}...")
        with open(os.path.join(path, "agent.yaml"), "r") as f:
            manifest = yaml.safe_load(f)
        
        # Resolve instructions file
        instr_file = manifest.get("instructions_file")
        with open(os.path.join(path, instr_file), "r") as f:
            manifest["instructions"] = f.read()

        response = requests.post(f"{self.base_url}/client/agents", headers=self.headers, json=manifest)
        if response.status_code == 201:
            print("Agent registered successfully.")
        else:
            print(f"Error registering agent: {response.status_code} - {response.text}")

    def run(self, agent_id, input_data):
        print(f"Running agent {agent_id}...")
        payload = {"input_data": json.loads(input_data)}
        response = requests.post(f"{self.base_url}/client/agents/{agent_id}/run", headers=self.headers, json=payload)
        print(json.dumps(response.json(), indent=2))

    def eval(self, agent_id):
        print(f"Running evals for agent {agent_id}...")
        response = requests.post(f"{self.base_url}/client/agents/{agent_id}/evals/run", headers=self.headers)
        print(json.dumps(response.json(), indent=2))

    def promote(self, agent_id, target):
        print(f"Promoting agent {agent_id} to {target}...")
        payload = {"target_status": target}
        response = requests.post(f"{self.base_url}/admin/agent-registry/{agent_id}/promote", headers=self.headers, json=payload)
        print(json.dumps(response.json(), indent=2))

    def logs(self, run_id):
        print(f"Fetching logs for run {run_id}...")
        response = requests.get(f"{self.base_url}/client/agents/runs/{run_id}/timeline", headers=self.headers)
        print(json.dumps(response.json(), indent=2))

def main():
    parser = argparse.ArgumentParser(description="Kleber AI Agent Control CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Init
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("name")
    init_parser.add_argument("--template", default="standard")

    # Validate
    val_parser = subparsers.add_parser("validate")
    val_parser.add_argument("path", default=".", nargs="?")

    # Register
    reg_parser = subparsers.add_parser("register")
    reg_parser.add_argument("path", default=".", nargs="?")

    # Run
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("agent_id")
    run_parser.add_argument("--input", default="{}")

    # Eval
    eval_parser = subparsers.add_parser("eval")
    eval_parser.add_argument("agent_id")

    # Promote
    prom_parser = subparsers.add_parser("promote")
    prom_parser.add_argument("agent_id")
    prom_parser.add_argument("target")

    # Logs
    log_parser = subparsers.add_parser("logs")
    log_parser.add_argument("run_id")

    args = parser.parse_args()
    ctl = AgentCTL()

    if args.command == "init":
        ctl.init(args.name, args.template)
    elif args.command == "validate":
        ctl.validate(args.path)
    elif args.command == "register":
        ctl.register(args.path)
    elif args.command == "run":
        ctl.run(args.agent_id, args.input)
    elif args.command == "eval":
        ctl.eval(args.agent_id)
    elif args.command == "promote":
        ctl.promote(args.agent_id, args.target)
    elif args.command == "logs":
        ctl.logs(args.run_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
