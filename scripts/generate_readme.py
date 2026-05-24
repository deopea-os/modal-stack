"""Generate the Config Reference section of README.md from the JSON schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCHEMA_PATH = _ROOT / "schemas" / "model-config.schema.json"
_README_PATH = _ROOT / "README.md"

_BEGIN_MARKER = "<!-- BEGIN GENERATED CONFIG REFERENCE -->"
_END_MARKER = "<!-- END GENERATED CONFIG REFERENCE -->"


def _load_schema() -> dict:
    with open(_SCHEMA_PATH) as f:
        return json.load(f)


def _resolve_ref(schema: dict, ref: str) -> dict:
    parts = ref.lstrip("#/").split("/")
    node = schema
    for part in parts:
        node = node[part]
    return node


def _format_default(value) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, str):
        return f'`"{value}"`'
    if isinstance(value, list) and len(value) == 0:
        return "`[]`"
    if isinstance(value, dict) and len(value) == 0:
        return "`{}`"
    return f"`{value}`"


def _truncate_description(desc: str) -> str:
    """Take only the first sentence for table cells."""
    first_sentence = desc.split(". ")[0]
    if not first_sentence.endswith("."):
        first_sentence += "."
    return first_sentence


def _generate_top_level_table(schema: dict) -> str:
    lines = []
    lines.append("| Field | Required | Default | Description |")
    lines.append("| ----- | -------- | ------- | ----------- |")

    required_fields = schema.get("required", [])
    props = schema.get("properties", {})

    for field_name, field_schema in props.items():
        is_required = field_name in required_fields
        required_str = "Yes" if is_required else "No"

        if "$ref" in field_schema:
            resolved = _resolve_ref(schema, field_schema["$ref"])
            desc = resolved.get("title", field_name.capitalize())
            if is_required:
                default_str = "—"
            else:
                default_str = "See below"
            desc_str = resolved.get("description", desc).split(".")[0]
        else:
            desc_str = _truncate_description(field_schema.get("description", ""))
            if is_required:
                default_str = "—"
            elif "default" in field_schema:
                default_str = _format_default(field_schema["default"])
            else:
                default_str = "Slug from `model.name`"

        lines.append(f"| `{field_name}` | {required_str} | {default_str} | {desc_str} |")

    return "\n".join(lines)


def _generate_section_table(schema: dict, def_name: str, *, include_required: bool = False) -> str:
    definition = schema["$defs"][def_name]
    props = definition.get("properties", {})
    required_fields = definition.get("required", [])

    lines = []
    if include_required:
        lines.append("| Field | Required | Default | Description |")
        lines.append("| ----- | -------- | ------- | ----------- |")
    else:
        lines.append("| Field | Default | Description |")
        lines.append("| ----- | ------- | ----------- |")

    for field_name, field_schema in props.items():
        is_required = field_name in required_fields
        desc = field_schema.get("description", "")
        desc_short = _truncate_description(desc)

        if is_required:
            default_str = "—"
            required_str = "**Yes**"
        else:
            default_val = field_schema.get("default")
            if "oneOf" in field_schema:
                default_val = field_schema.get("default")
            default_str = _format_default(default_val)
            required_str = "No"

        if include_required:
            lines.append(f"| `{field_name}` | {required_str} | {default_str} | {desc_short} |")
        else:
            lines.append(f"| `{field_name}` | {default_str} | {desc_short} |")

    return "\n".join(lines)


def _generate_gpu_types_table(schema: dict) -> str:
    gpu_def = schema["$defs"]["GpuConfig"]
    gpu_type_field = gpu_def["properties"]["type"]
    gpu_types = gpu_type_field.get("x-gpu-types", {}).get("types", [])

    if not gpu_types:
        return ""

    lines = []
    lines.append("**Available GPU types:**")
    lines.append("")
    lines.append("| GPU | Memory | Architecture | Max Count | Notes |")
    lines.append("| --- | ------ | ------------ | --------- | ----- |")

    for gpu in gpu_types:
        lines.append(
            f"| `{gpu['id']}` | {gpu['memory_gb']} GB | {gpu['architecture']} "
            f"| {gpu['max_count']} | {gpu['notes']} |"
        )

    return "\n".join(lines)


def _generate_sizing_guide(schema: dict) -> str:
    gpu_def = schema["$defs"]["GpuConfig"]
    gpu_type_field = gpu_def["properties"]["type"]
    guide = gpu_type_field.get("x-sizing-guide", {})
    recs = guide.get("recommendations", [])

    if not recs:
        return ""

    lines = []
    lines.append("**Sizing guide:**")
    lines.append("")
    lines.append("| Model size | Recommended GPU | Count |")
    lines.append("| ---------- | --------------- | ----- |")

    for rec in recs:
        lines.append(f"| {rec['model_size']} | {rec['gpu']} | {rec['count']} |")

    return "\n".join(lines)


def _generate_common_patterns(schema: dict) -> str:
    vllm_def = schema["$defs"]["VllmArgsConfig"]
    extra_args_field = vllm_def["properties"]["extra_args"]
    patterns = extra_args_field.get("x-common-patterns", {}).get("patterns", [])

    if not patterns:
        return ""

    lines = []
    lines.append("Common `extra_args` patterns:")
    lines.append("")
    lines.append("```yaml")

    for i, pattern in enumerate(patterns):
        if i > 0:
            lines.append("")
        lines.append(f"# {pattern['name']}")
        if pattern.get("description"):
            lines.append(f"# {pattern['description']}")
        lines.append("extra_args:")
        for arg in pattern["example"]:
            if arg.startswith("{"):
                lines.append(f"  - '{arg}'")
            else:
                lines.append(f'  - "{arg}"')

    lines.append("```")
    return "\n".join(lines)


def _generate_common_env_vars(schema: dict) -> str:
    image_def = schema["$defs"]["ImageConfig"]
    env_field = image_def["properties"]["env"]
    env_vars = env_field.get("x-common-env-vars", {}).get("variables", [])

    if not env_vars:
        return ""

    lines = []
    lines.append("Common environment variables:")
    lines.append("")
    lines.append("| Variable | Value | Description |")
    lines.append("| -------- | ----- | ----------- |")

    for var in env_vars:
        lines.append(f"| `{var['name']}` | `\"{var['value']}\"` | {var['description']} |")

    return "\n".join(lines)


def generate_config_reference() -> str:
    schema = _load_schema()
    sections = []

    sections.append("## Config Reference")
    sections.append("")
    sections.append("All fields except `model.name` are optional. Defaults are shown below.")
    sections.append("")

    # Top-level table
    sections.append("### Top-level")
    sections.append("")
    sections.append(_generate_top_level_table(schema))
    sections.append("")

    # model section
    sections.append("### `model`")
    sections.append("")
    sections.append(_generate_section_table(schema, "ModelSection", include_required=True))
    sections.append("")

    # engine section
    sections.append("### `engine`")
    sections.append("")
    sections.append(_generate_section_table(schema, "EngineConfig"))
    sections.append("")

    # gpu section
    sections.append("### `gpu`")
    sections.append("")
    sections.append(_generate_section_table(schema, "GpuConfig"))
    sections.append("")
    sections.append(_generate_gpu_types_table(schema))
    sections.append("")
    sections.append(_generate_sizing_guide(schema))
    sections.append("")

    # scaling section
    sections.append("### `scaling`")
    sections.append("")
    sections.append(_generate_section_table(schema, "ScalingConfig"))
    sections.append("")

    # vllm_args section
    sections.append("### `vllm_args`")
    sections.append("")
    sections.append(_generate_section_table(schema, "VllmArgsConfig"))
    sections.append("")
    sections.append(_generate_common_patterns(schema))
    sections.append("")

    # image section
    sections.append("### `image`")
    sections.append("")
    sections.append(_generate_section_table(schema, "ImageConfig"))
    sections.append("")
    sections.append(_generate_common_env_vars(schema))
    sections.append("")

    # volumes section
    sections.append("### `volumes`")
    sections.append("")
    sections.append(_generate_section_table(schema, "VolumesConfig"))
    sections.append("")

    volumes_def = schema["$defs"]["VolumesConfig"]
    volumes_desc = volumes_def.get("description", "")
    note_parts = volumes_desc.split(". ", 1)
    if len(note_parts) > 1:
        sections.append(f"{note_parts[0]}. {note_parts[1]}")
    else:
        sections.append(volumes_desc)
    sections.append("")

    sections.append("### `auth`")
    sections.append("")
    sections.append(_generate_section_table(schema, "AuthConfig", include_required=True))
    sections.append("")

    auth_def = schema["$defs"]["AuthConfig"]
    auth_desc = auth_def.get("description", "")
    sections.append(auth_desc)
    sections.append("")
    sections.append(
        "Create the secret with `modal secret create <token_name> AUTH_TOKEN=<your-token>`. "
        "The secret must define an `AUTH_TOKEN` key. "
        "vLLM enforces Bearer auth on `/v1` endpoints when auth is enabled. "
        "Pass the secret name at deploy or run time: "
        "`agents deploy <config> -t <token_name>` (or set `AUTH_TOKEN_NAME` in the environment)."
    )

    return "\n".join(sections)


def update_readme(*, check: bool = False) -> bool:
    """Replace the Config Reference section in README.md.

    Returns True if the file was (or would be) changed.
    """
    generated = generate_config_reference()
    readme_text = _README_PATH.read_text()

    begin_idx = readme_text.find(_BEGIN_MARKER)
    end_idx = readme_text.find(_END_MARKER)

    if begin_idx == -1 or end_idx == -1:
        print(
            f"ERROR: Could not find markers in {_README_PATH}.\n"
            f"Expected:\n  {_BEGIN_MARKER}\n  {_END_MARKER}",
            file=sys.stderr,
        )
        sys.exit(1)

    new_section = f"{_BEGIN_MARKER}\n{generated}\n{_END_MARKER}"
    new_readme = readme_text[:begin_idx] + new_section + readme_text[end_idx + len(_END_MARKER):]

    if new_readme == readme_text:
        return False

    if check:
        return True

    _README_PATH.write_text(new_readme)
    return True


def main() -> None:
    check = "--check" in sys.argv

    changed = update_readme(check=check)

    if check:
        if changed:
            print("README.md is out of date. Run 'agents generate-docs' to update.", file=sys.stderr)
            sys.exit(1)
        else:
            print("README.md is up to date.")
    else:
        if changed:
            print(f"Updated {_README_PATH.relative_to(_ROOT)}")
        else:
            print("README.md is already up to date. No changes made.")


if __name__ == "__main__":
    main()
