import argparse
import os
import sys

# Ensure project root is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentCTL:
    def __init__(self):
        self.parser = argparse.ArgumentParser(prog="agentctl")
        subparsers = self.parser.add_subparsers(dest="command")

        # init (legacy/top-level)
        init_parser = subparsers.add_parser("init")
        init_parser.add_argument("name")
        # Removed --template as it's not supported by agent-bundle-init.sh

        # validate (integrated)
        validate_parser = subparsers.add_parser("validate", help="Validate a workflow file")
        validate_parser.add_argument("path", help="Path to workflow YAML")
        validate_parser.add_argument("--json", action="store_true")

        # explain (integrated)
        explain_parser = subparsers.add_parser("explain", help="Explain workflow steps")
        explain_parser.add_argument("path", help="Path to workflow YAML")

        # bundle
        bundle_parser = subparsers.add_parser("bundle")
        bundle_sub = bundle_parser.add_subparsers(dest="subcommand")

        # bundle init
        b_init = bundle_sub.add_parser("init")
        b_init.add_argument("name")
        b_init.add_argument("dir", nargs="?", default=None)

        # bundle validate
        b_val = bundle_sub.add_parser("validate")
        b_val.add_argument("path", nargs="?", default=".")

        # bundle test
        b_test = bundle_sub.add_parser("test")
        b_test.add_argument("path", nargs="?", default=".")

        # bundle sign
        b_sign = bundle_sub.add_parser("sign")
        b_sign.add_argument("path", nargs="?", default=".")
        b_sign.add_argument("--key", help="Path to ed25519 pem key")

        # bundle publish
        b_pub = bundle_sub.add_parser("publish")
        b_pub.add_argument("path", nargs="?", default=".")

        # run (integrated from new agentctl)
        run_p = subparsers.add_parser("run", help="Run a workflow")
        run_p.add_argument("path", help="Path to workflow YAML")
        run_p.add_argument("--watch", action="store_true")
        run_p.add_argument("--debug", action="store_true")
        run_p.add_argument("--trace", action="store_true")
        run_p.add_argument("--json", action="store_true")

        # costs (integrated)
        costs_p = subparsers.add_parser("costs", help="Show cost attribution")
        costs_p.add_argument("--agent", help="Filter by agent ID")
        costs_p.add_argument("--json", action="store_true")

        # replay (integrated)
        rep_p = subparsers.add_parser("replay", help="Replay a workflow run")
        rep_p.add_argument("run_id", help="ID of the run to replay")
        rep_p.add_argument("--dry-run", action="store_true")
        rep_p.add_argument("--json", action="store_true")
        rep_p.add_argument("--yes", "-y", action="store_true")

        # eval (integrated)
        eval_p = subparsers.add_parser("eval", help="Evaluation management")
        eval_sub = eval_p.add_subparsers(dest="subcommand")
        eval_run_p = eval_sub.add_parser("run", help="Run evaluation dataset")
        eval_run_p.add_argument("path", help="Path to dataset YAML")
        eval_run_p.add_argument("--json", action="store_true")

        # policies (integrated)
        pol_p = subparsers.add_parser("policies", help="Policy management")
        pol_sub = pol_p.add_subparsers(dest="subcommand")
        pol_test_p = pol_sub.add_parser("test", help="Test a policy")
        pol_test_p.add_argument("path", help="Path to policy YAML")
        pol_test_p.add_argument("--json", action="store_true")

        # backends (integrated)
        back_p = subparsers.add_parser("backends", help="Backend management")
        back_sub = back_p.add_subparsers(dest="subcommand")
        back_list_p = back_sub.add_parser("list", help="List all backends")
        back_list_p.add_argument("--json", action="store_true")

    def init(self, name):
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cmd = [f"{script_dir}/agent-bundle-init.sh", name]
        import subprocess
        subprocess.run(cmd, check=True)

    def validate(self, path):
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "manifest.json")):
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cmd = [f"{script_dir}/agent-bundle-validate.sh", path]
            import subprocess
            subprocess.run(cmd, check=True)
            return
        from scripts.agentctl_pkg.main import validate_workflow
        validate_workflow(path)

    def bundle(self, dir_path, output_path):
        import shutil
        shutil.make_archive(output_path.replace(".zip", ""), 'zip', dir_path)

    def run(self):
        args = self.parser.parse_args()
        if not args.command:
            self.parser.print_help()
            return

        if args.command == "init":
            self.init(args.name)
        elif args.command == "validate":
            from scripts.agentctl_pkg.main import validate_workflow
            validate_workflow(args.path, use_json=getattr(args, "json", False))
        elif args.command == "explain":
            from scripts.agentctl_pkg.main import explain_workflow
            explain_workflow(args.path)
        elif args.command == "run":
            from scripts.agentctl_pkg.main import run_workflow
            run_workflow(args.path, watch=args.watch, debug=args.debug, trace=args.trace, use_json=args.json)
        elif args.command == "costs":
            from scripts.agentctl_pkg.main import show_costs
            show_costs(agent_id=args.agent, use_json=args.json)
        elif args.command == "replay":
            from scripts.agentctl_pkg.main import replay_run
            replay_run(args.run_id, dry_run=args.dry_run, use_json=args.json)
        elif args.command == "eval":
            from scripts.agentctl_pkg.main import run_eval
            if args.subcommand == "run":
                run_eval(args.path, use_json=args.json)
        elif args.command == "policies":
            from scripts.agentctl_pkg.main import test_policy
            if args.subcommand == "test":
                test_policy(args.path, use_json=args.json)
        elif args.command == "backends":
            from scripts.agentctl_pkg.main import list_backends
            if args.subcommand == "list":
                list_backends(use_json=args.json)
        elif args.command == "bundle":
            self.handle_bundle(args)

    def handle_bundle(self, args):
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if args.subcommand == "init":
            cmd = [f"{script_dir}/agent-bundle-init.sh", args.name]
            if args.dir: cmd.append(args.dir)
            os.execv(cmd[0], cmd)
        elif args.subcommand == "validate":
            cmd = [f"{script_dir}/agent-bundle-validate.sh", args.path]
            os.execv(cmd[0], cmd)
        elif args.subcommand == "test":
            cmd = [f"{script_dir}/agent-bundle-test.sh", args.path]
            os.execv(cmd[0], cmd)
        elif args.subcommand == "sign":
            cmd = [f"{script_dir}/agent-bundle-sign.sh", args.path]
            if args.key: cmd.append(args.key)
            os.execv(cmd[0], cmd)
        elif args.subcommand == "publish":
            cmd = [f"{script_dir}/agent-bundle-publish.sh", args.path]
            os.execv(cmd[0], cmd)
