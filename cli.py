import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).parent


def _resolve_config(name: str) -> None:
    config_path = _ROOT / "configs" / f"{name}.yaml"
    if not config_path.exists():
        available = sorted(
            p.stem for p in (_ROOT / "configs").glob("*.yaml")
            if not p.stem.startswith("_")
        )
        print(f"Config '{name}' not found.", file=sys.stderr)
        print(f"Available: {', '.join(available) or '(none)'}", file=sys.stderr)
        sys.exit(1)


def _cmd_deploy(args: argparse.Namespace) -> None:
    _resolve_config(args.config)
    main_py = str(_ROOT / "main.py")
    subprocess.run(
        ["modal", "deploy", main_py],
        env={**os.environ, "MODEL_CONFIG": args.config},
        check=True,
    )


def _cmd_run(args: argparse.Namespace) -> None:
    _resolve_config(args.config)
    main_py = str(_ROOT / "main.py")
    subprocess.run(
        ["modal", "run", main_py, "--", "--config", args.config],
        check=True,
    )


def _cmd_generate_docs(args: argparse.Namespace) -> None:
    from scripts.generate_readme import update_readme

    changed = update_readme(check=args.check)

    if args.check:
        if changed:
            print(
                "README.md is out of date. Run 'agents generate-docs' to update.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            print("README.md is up to date.")
    else:
        if changed:
            print(f"Updated README.md")
        else:
            print("README.md is already up to date. No changes made.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents",
        description="Deploy and run Modal LLM serving configs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    deploy_p = sub.add_parser("deploy", help="Deploy a model config to Modal")
    deploy_p.add_argument("config", help="Config name (resolves to configs/<name>.yaml)")

    run_p = sub.add_parser("run", help="Spin up a model and run a health check")
    run_p.add_argument("config", help="Config name (resolves to configs/<name>.yaml)")

    docs_p = sub.add_parser(
        "generate-docs",
        help="Regenerate README.md Config Reference from the JSON schema",
    )
    docs_p.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if README is out of date (for CI)",
    )

    args = parser.parse_args()

    if args.command == "deploy":
        _cmd_deploy(args)
    elif args.command == "run":
        _cmd_run(args)
    elif args.command == "generate-docs":
        _cmd_generate_docs(args)


if __name__ == "__main__":
    main()
