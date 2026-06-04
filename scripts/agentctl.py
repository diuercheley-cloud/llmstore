#!/usr/bin/env python3
import argparse
import os
import sys


class AgentCTL:
    def __init__(self):
        self.parser = argparse.ArgumentParser(prog="agentctl")
        subparsers = self.parser.add_subparsers(dest="command")

        # init (legacy/top-level)
        init_parser = subparsers.add_parser("init")
        init_parser.add_argument("name")
        init_parser.add_argument("--template", default="support-triage")

        # validate (legacy/top-level)
        validate_parser = subparsers.add_parser("validate")
        validate_parser.add_argument("path", nargs="?", default=".")

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
            self.handle_bundle(args)

    def handle_bundle(self, args):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
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
        else:
            print("Usage: agentctl bundle {init,validate,test,sign,publish}")
            sys.exit(1)

if __name__ == "__main__":
    ctl = AgentCTL()
    ctl.run()
