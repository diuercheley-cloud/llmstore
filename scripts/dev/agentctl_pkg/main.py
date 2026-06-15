import argparse
import os
import sys
import time

import httpx

from scripts.agentctl_pkg.utils import (
    CLIColor,
    confirm_action,
    format_output,
    load_yaml,
    redact_sensitive_data,
)

API_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")


def get_client():
    return httpx.Client(base_url=API_URL, headers={"X-Admin-Token": ADMIN_TOKEN}, timeout=30.0)


def validate_workflow(path: str, use_json: bool = False):
    workflow = load_yaml(path)
    # Perform offline validation
    errors = []
    if "name" not in workflow:
        errors.append("Missing 'name'")
    if "steps" not in workflow:
        errors.append("Missing 'steps'")

    if errors:
        print(f"{CLIColor.FAIL}Validation failed:{CLIColor.ENDC}")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print(f"{CLIColor.OKGREEN}Workflow '{workflow['name']}' is valid.{CLIColor.ENDC}")
    if use_json:
        format_output({"status": "valid", "name": workflow["name"]}, True)


def explain_workflow(path: str):
    workflow = load_yaml(path)
    print(f"{CLIColor.BOLD}Workflow: {workflow.get('name', 'Unnamed')}{CLIColor.ENDC}")
    print(f"Description: {workflow.get('description', 'N/A')}")
    print(f"\n{CLIColor.HEADER}Steps:{CLIColor.ENDC}")
    for i, step in enumerate(workflow.get("steps", [])):
        print(f"  {i + 1}. {step.get('name', 'Unnamed step')} ({step.get('type', 'generic')})")
        if "tool" in step:
            print(f"     Tool: {step['tool']}")


def run_workflow(
    path: str, watch: bool = False, debug: bool = False, trace: bool = False, use_json: bool = False
):
    workflow = load_yaml(path)

    try:
        with get_client() as client:
            resp = client.post("/api/v1/admin/workflows/run", json=workflow)
            if resp.status_code != 200:
                print(
                    f"{CLIColor.FAIL}Failed to start workflow: {resp.text}{CLIColor.ENDC}",
                    file=sys.stderr,
                )
                sys.exit(1)

            run_data = resp.json()
            run_id = run_data["run_id"]
            print(f"{CLIColor.OKBLUE}Workflow started. Run ID: {run_id}{CLIColor.ENDC}")

            if watch:
                watch_run(run_id, debug=debug, trace=trace, use_json=use_json)
            else:
                format_output(run_data, use_json)

    except httpx.ConnectError:
        print(
            f"{CLIColor.FAIL}Error: Control Plane API at {API_URL} is unavailable.{CLIColor.ENDC}",
            file=sys.stderr,
        )
        sys.exit(1)


def watch_run(run_id: str, debug: bool = False, trace: bool = False, use_json: bool = False):
    print(f"Watching run {run_id}...")
    completed = False
    while not completed:
        try:
            with get_client() as client:
                resp = client.get(f"/api/v1/admin/workflows/runs/{run_id}")
                status_data = resp.json()

                if use_json:
                    print(json.dumps(redact_sensitive_data(status_data)))
                else:
                    status = status_data.get("status", "unknown")
                    print(f"Status: {status}")
                    if trace and "events" in status_data:
                        for event in status_data["events"]:
                            print(f"  [{event['timestamp']}] {event['type']}: {event['message']}")

                    if status in ("completed", "failed"):
                        completed = True

                if not completed:
                    time.sleep(2)
        except Exception as e:
            print(f"Error polling status: {e}")
            break


def replay_run(run_id: str, dry_run: bool = False, use_json: bool = False):
    if not confirm_action(f"Replay run {run_id}?"):
        return

    try:
        with get_client() as client:
            resp = client.post(
                f"/api/v1/admin/workflows/runs/{run_id}/replay", params={"dry_run": dry_run}
            )
            resp.raise_for_status()
            format_output(resp.json(), use_json)
    except Exception as e:
        print(f"{CLIColor.FAIL}Replay failed: {e}{CLIColor.ENDC}", file=sys.stderr)
        sys.exit(1)


def show_costs(agent_id: str | None = None, use_json: bool = False):
    try:
        with get_client() as client:
            params = {"agent_id": agent_id} if agent_id else {}
            resp = client.get("/api/admin/costs/summary", params=params)
            resp.raise_for_status()
            format_output(resp.json(), use_json)
    except Exception as e:
        print(f"{CLIColor.FAIL}Failed to fetch costs: {e}{CLIColor.ENDC}", file=sys.stderr)
        sys.exit(1)


def list_backends(use_json: bool = False):
    try:
        with get_client() as client:
            resp = client.get("/admin/backends")
            resp.raise_for_status()
            format_output(resp.json(), use_json)
    except Exception as e:
        print(f"{CLIColor.FAIL}Failed to list backends: {e}{CLIColor.ENDC}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="agentctl", description="CLI for managing agents and workflows"
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm actions")

    subparsers = parser.add_subparsers(dest="command")

    # run
    run_p = subparsers.add_parser("run", help="Run a workflow")
    run_p.add_argument("path", help="Path to workflow YAML")
    run_p.add_argument("--watch", action="store_true")
    run_p.add_argument("--debug", action="store_true")
    run_p.add_argument("--trace", action="store_true")

    # validate
    val_p = subparsers.add_parser("validate", help="Validate a workflow file")
    val_p.add_argument("path", help="Path to workflow YAML")

    # explain
    exp_p = subparsers.add_parser("explain", help="Explain workflow steps")
    exp_p.add_argument("path", help="Path to workflow YAML")

    # replay
    rep_p = subparsers.add_parser("replay", help="Replay a workflow run")
    rep_p.add_argument("run_id", help="ID of the run to replay")
    rep_p.add_argument("--dry-run", action="store_true")

    # costs
    costs_p = subparsers.add_parser("costs", help="Show cost attribution")
    costs_p.add_argument("--agent", help="Filter by agent ID")

    # backends
    back_p = subparsers.add_parser("backends", help="Backend management")
    back_sub = back_p.add_subparsers(dest="subcommand")
    back_sub.add_parser("list", help="List all backends")

    # eval
    eval_p = subparsers.add_parser("eval", help="Evaluation management")
    eval_sub = eval_p.add_subparsers(dest="subcommand")
    eval_run_p = eval_sub.add_parser("run", help="Run evaluation dataset")
    eval_run_p.add_argument("path", help="Path to dataset YAML")

    # policies
    pol_p = subparsers.add_parser("policies", help="Policy management")
    pol_sub = pol_p.add_subparsers(dest="subcommand")
    pol_test_p = pol_sub.add_parser("test", help="Test a policy")
    pol_test_p.add_argument("path", help="Path to policy YAML")

    args = parser.parse_args()

    if args.command == "run":
        run_workflow(
            args.path, watch=args.watch, debug=args.debug, trace=args.trace, use_json=args.json
        )
    elif args.command == "validate":
        validate_workflow(args.path, use_json=args.json)
    elif args.command == "explain":
        explain_workflow(args.path)
    elif args.command == "replay":
        replay_run(args.run_id, dry_run=args.dry_run, use_json=args.json)
    elif args.command == "costs":
        show_costs(agent_id=args.agent, use_json=args.json)
    elif args.command == "backends":
        if args.subcommand == "list":
            list_backends(use_json=args.json)
    elif args.command == "eval":
        if args.subcommand == "run":
            run_eval(args.path, use_json=args.json)
    elif args.command == "policies":
        if args.subcommand == "test":
            test_policy(args.path, use_json=args.json)
    else:
        parser.print_help()


def run_eval(path: str, use_json: bool = False):
    dataset = load_yaml(path)
    try:
        with get_client() as client:
            resp = client.post("/admin/evaluation/runs", json=dataset)
            resp.raise_for_status()
            format_output(resp.json(), use_json)
    except Exception as e:
        print(f"{CLIColor.FAIL}Eval failed: {e}{CLIColor.ENDC}", file=sys.stderr)
        sys.exit(1)


def test_policy(path: str, use_json: bool = False):
    policy = load_yaml(path)
    try:
        with get_client() as client:
            resp = client.post("/api/v1/admin/policies/test", json=policy)
            resp.raise_for_status()
            format_output(resp.json(), use_json)
    except Exception as e:
        print(f"{CLIColor.FAIL}Policy test failed: {e}{CLIColor.ENDC}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
