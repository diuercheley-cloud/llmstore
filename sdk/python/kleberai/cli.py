"""agentctl CLI - Manage agents from the command line."""

import argparse
import json

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

    # agent create (from file)
    create_p = sub.add_parser("create", help="Create agent from JSON file")
    create_p.add_argument("file", help="Path to agent manifest JSON")

    # scaffold (from template)
    scaffold_p = sub.add_parser("scaffold", help="Scaffold a new agent from a template")
    scaffold_p.add_argument("template", help="Template name (use 'list-templates' to see available)")
    scaffold_p.add_argument("--name", "-n", default=None, help="Agent name")
    scaffold_p.add_argument("--output", "-o", default=".", help="Output directory")
    scaffold_p.add_argument("--force", "-f", action="store_true", help="Overwrite existing directory")

    sub.add_parser("list-templates", help="List available agent scaffolding templates")

    # health
    sub.add_parser("health", help="Check API health")

    # models
    sub.add_parser("models", help="List models")

    # studio flows
    studio_p = sub.add_parser("studio-flows", help="List studio flows")

    # backup
    backup_p = sub.add_parser("backup", help="Backup agent configurations")
    backup_p.add_argument("agent_ids", nargs="+", help="Agent IDs to backup")
    backup_p.add_argument("--type", default="full", choices=["full", "config-only"], help="Backup type")
    backup_p.add_argument("--include-memory", action="store_true", default=True, help="Include agent memory")
    backup_p.add_argument("--include-runs", action="store_true", default=True, help="Include run history")

    backup_list_p = sub.add_parser("backup-list", help="List available backups")
    backup_list_p.add_argument("--agent-id", default=None, help="Filter by agent ID")

    restore_p = sub.add_parser("restore", help="Restore agent from backup")
    restore_p.add_argument("backup_id", help="Backup ID")
    restore_p.add_argument("--agent-ids", nargs="*", help="Specific agents to restore (default: all)")

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

    elif args.command == "scaffold":
        from kleberai.scaffold import scaffold as _scaffold
        values = {}
        if args.name:
            values["name"] = args.name
        output = _scaffold(args.template, args.output, values=values, force=args.force)
        print(f"Agent scaffolded at: {output}")

    elif args.command == "list-templates":
        from kleberai.scaffold import list_templates as _list_templates
        templates = _list_templates()
        for t in templates:
            status = "✓" if t["exists"] else "✗"
            print(f"  {status} {t['id']:30s} {t['description']}")

    elif args.command == "health":
        status = client.system.health()
        print(json.dumps(status, indent=2, default=str))

    elif args.command == "models":
        models = client.models()
        print(json.dumps(models, indent=2, default=str))

    elif args.command == "studio-flows":
        flows = client.studio.list_flows()
        print(json.dumps(flows, indent=2, default=str))

    elif args.command == "backup":
        result = client.backup.create(
            agent_ids=args.agent_ids,
            backup_type=args.type,
            include_memory=args.include_memory,
            include_runs=args.include_runs,
        )
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "backup-list":
        result = client.backup.list(agent_id=args.agent_id)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "restore":
        result = client.backup.restore(args.backup_id, agent_ids=args.agent_ids)
        print(json.dumps(result, indent=2, default=str))

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
