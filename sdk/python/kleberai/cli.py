"""agentctl CLI - Manage agents from the command line."""

import argparse
import json
import sys

from kleberai import Client


def main():
    parser = argparse.ArgumentParser(description="Kleber AI Agent CLI")
    parser.add_argument("--api-key", default=None, help="API key")
    parser.add_argument("--base-url", default="http://localhost:18080", help="Base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    # agent list
    sub.add_parser("list", help="List agents")

    # agent get
    get_p = sub.add_parser("get", help="Get agent details")
    get_p.add_argument("agent_id", help="Agent ID")

    # agent run
    run_p = sub.add_parser("run", help="Run an agent")
    run_p.add_argument("agent_id", help="Agent ID")
    run_p.add_argument("--input", "-i", required=True, help="Input prompt")

    # agent create
    create_p = sub.add_parser("create", help="Create agent from JSON file")
    create_p.add_argument("file", help="Path to agent manifest JSON")

    # health
    sub.add_parser("health", help="Check API health")

    # models
    sub.add_parser("models", help="List models")

    # studio flows
    studio_p = sub.add_parser("studio-flows", help="List studio flows")

    # eval subcommands
    eval_p = sub.add_parser("eval", help="Run agent evaluations")
    eval_sub = eval_p.add_subparsers(dest="eval_command", required=True)

    eval_run = eval_sub.add_parser("run", help="Run eval suite against an agent")
    eval_run.add_argument("agent_id", help="Agent ID")
    eval_run.add_argument("--suite", help="Suite ID (optional)", default=None)

    eval_list = eval_sub.add_parser("list", help="List eval reports")
    eval_list.add_argument("agent_id", help="Agent ID")

    eval_suites = eval_sub.add_parser("suites", help="List available eval suites")
    eval_suites.add_argument("--agent-id", help="Filter by agent ID", default=None)

    args = parser.parse_args()

    client = Client(api_key=args.api_key or "", base_url=args.base_url)

    if args.command == "list":
        agents = client.agents.list()
        print(json.dumps(agents, indent=2, default=str))

    elif args.command == "get":
        agent = client.agents.get(args.agent_id)
        print(json.dumps(agent, indent=2, default=str))

    elif args.command == "run":
        result = client.agents.run(args.agent_id, {"prompt": args.input})
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "create":
        with open(args.file) as f:
            manifest = json.load(f)
        agent = client.agents.create(manifest)
        print(json.dumps(agent, indent=2, default=str))

    elif args.command == "health":
        status = client.system.health()
        print(json.dumps(status, indent=2, default=str))

    elif args.command == "models":
        models = client.models()
        print(json.dumps(models, indent=2, default=str))

    elif args.command == "studio-flows":
        flows = client.studio.list_flows()
        print(json.dumps(flows, indent=2, default=str))

    elif args.command == "eval":
        if args.eval_command == "run":
            result = client.agent_evals.run(args.agent_id, suite_id=args.suite)
            print(json.dumps(result, indent=2, default=str))
        elif args.eval_command == "list":
            reports = client.agent_evals.get_reports(args.agent_id)
            print(json.dumps(reports, indent=2, default=str))
        elif args.eval_command == "suites":
            suites = client.agent_evals.list_suites(args.agent_id)
            print(json.dumps(suites, indent=2, default=str))


if __name__ == "__main__":
    main()
