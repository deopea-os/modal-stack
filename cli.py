import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).parent

# Editable installs only map top-level packages declared at install time; ensure
# `scripts/` is importable when running the `agents` console script.
_root_str = str(_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)


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


def _modal_env(config_name: str, token_name: str | None) -> dict[str, str]:
    env = {**os.environ, "MODEL_CONFIG": config_name}
    if token_name:
        env["AUTH_TOKEN_NAME"] = token_name
    return env


def _add_token_name_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-t",
        "--token-name",
        metavar="NAME",
        help="Modal Secret name for AUTH_TOKEN (not stored in config YAML). "
        "Create with: modal secret create NAME AUTH_TOKEN=<token>",
    )


def _cmd_deploy(args: argparse.Namespace) -> None:
    _resolve_config(args.config)
    main_py = str(_ROOT / "main.py")
    subprocess.run(
        ["modal", "deploy", main_py],
        env=_modal_env(args.config, args.token_name),
        check=True,
    )


def _cmd_run(args: argparse.Namespace) -> None:
    _resolve_config(args.config)
    main_py = str(_ROOT / "main.py")
    subprocess.run(
        ["modal", "run", main_py, "--", "--config", args.config],
        env=_modal_env(args.config, args.token_name),
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
            print("Updated README.md")
        else:
            print("README.md is already up to date. No changes made.")


def _cmd_generate_config(args: argparse.Namespace) -> None:
    from scripts.generate_config import generate_config

    changed = generate_config(check=args.check)

    if args.check:
        if changed:
            print(
                "models/_generated.py is out of date. "
                "Run 'agents generate-config' to update.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            print("models/_generated.py is up to date.")
    else:
        if changed:
            print("Updated models/_generated.py")
        else:
            print("models/_generated.py is already up to date. No changes made.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents",
        description="Deploy and run Modal LLM serving configs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    deploy_p = sub.add_parser("deploy", help="Deploy a model config to Modal")
    deploy_p.add_argument("config", help="Config name (resolves to configs/<name>.yaml)")
    _add_token_name_arg(deploy_p)

    run_p = sub.add_parser("run", help="Spin up a model and run a health check")
    run_p.add_argument("config", help="Config name (resolves to configs/<name>.yaml)")
    _add_token_name_arg(run_p)

    docs_p = sub.add_parser(
        "generate-docs",
        help="Regenerate README.md Config Reference from the JSON schema",
    )
    docs_p.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if README is out of date (for CI)",
    )

    config_p = sub.add_parser(
        "generate-config",
        help="Regenerate models/_generated.py from the JSON schema",
    )
    config_p.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if generated config is out of date (for CI)",
    )

    args = parser.parse_args()

    if args.command == "deploy":
        _cmd_deploy(args)
    elif args.command == "run":
        _cmd_run(args)
    elif args.command == "generate-docs":
        _cmd_generate_docs(args)
    elif args.command == "generate-config":
        _cmd_generate_config(args)


if __name__ == "__main__":
    main()
