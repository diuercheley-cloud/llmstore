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


if __name__ == "__main__":
    main()
