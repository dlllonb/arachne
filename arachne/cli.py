"""Command-line interface for Arachne."""

import argparse
import sys
from pathlib import Path

from arachne import instance, engine


def main():
    """Entry point for the arachne command."""
    # Check if first arg is a known subcommand
    if len(sys.argv) > 1 and sys.argv[1] in ("init", "prompt", "reset"):
        # Use argparse for explicit subcommands
        parser = argparse.ArgumentParser(description="Arachne - Local Project AI Assistant")
        subparsers = parser.add_subparsers(dest="command", required=True)
        
        # Init command
        init_parser = subparsers.add_parser("init", help="Initialize an Arachne instance")
        init_parser.add_argument("name", nargs="?", help="Project name (optional)")
        
        # Prompt command
        prompt_parser = subparsers.add_parser("prompt", help="Build and display prompt")
        prompt_parser.add_argument("query", help="Query/request for Arachne")
        
        # Reset command
        reset_parser = subparsers.add_parser("reset", help="Clear history and memory")
        
        args = parser.parse_args()
        
        if args.command == "init":
            root = Path.cwd()
            # Check if an instance already exists in the tree
            existing = instance.check_existing_instance_in_tree(root)
            if existing:
                print(f"Error: Arachne instance already exists at {existing}")
                print("Use that instance instead, or initialize in a different directory.")
                sys.exit(1)
            instance.init_instance(root, args.name)
            print(f"Arachne instance initialized at {root}")
            return
        
        if args.command == "prompt":
            root = instance.find_instance_root()
            if not root:
                print("Error: No Arachne instance found.")
                print("Run 'arachne init' in your project root.")
                sys.exit(1)
            response = engine.query(args.query, root)
            print(response)
            return
        
        if args.command == "reset":
            root = instance.find_instance_root()
            if not root:
                print("Error: No Arachne instance found.")
                print("Run 'arachne init' in your project root.")
                sys.exit(1)
            confirm = input(f"Clear history and memory for instance at {root}? (y/n): ")
            if confirm.lower() == "y":
                instance.reset_instance(root)
                print("Instance reset.")
            else:
                print("Cancelled.")
            return
    else:
        # Fallback: treat all args as a query
        if len(sys.argv) > 1:
            root = instance.find_instance_root()
            if not root:
                print("Error: No Arachne instance found.")
                print("Run 'arachne init [<project_name>]' in your project root.")
                sys.exit(1)
            user_input = " ".join(sys.argv[1:])
            response = engine.query(user_input, root)
            print(response)
            return
        
        # No args provided
        parser = argparse.ArgumentParser(description="Arachne - Local Project AI Assistant")
        parser.print_help()



if __name__ == "__main__":
    main()

