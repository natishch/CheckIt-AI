import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# --- CONFIGURATION ---
root: Path = Path(__file__).resolve().parent
print(f"{root = }")
file_meta_path: Path = root / "impl-tasks-with-priority-and-dependencies.json"
file_prompts_path: Path = root / "impl-tasks-with-prompts.json"


def load_json(file_path: Path) -> list[dict[str, Any]]:
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("tasks", [])
    except FileNotFoundError:
        print(f"❌ Error: Could not find file '{file_path}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: File '{file_path}' is not valid JSON")
        sys.exit(1)


def merge_tasks(
    meta_tasks: list[dict[str, str | list[str]]], prompt_tasks: list[dict[str, str]]
) -> list[dict[str, str | list[str]]]:
    merged: list[dict[str, str | list[str]]] = []
    print(f"🔄 Merging {len(meta_tasks)} meta tasks with {len(prompt_tasks)} prompt tasks...")

    # Assume same length and same order
    for i, meta in enumerate(meta_tasks):
        if i < len(prompt_tasks):
            match = prompt_tasks[i]
            # Combine the data
            combined = {
                **meta,  # priorities, ids, deps
                "developer_guide_prompt": match.get(
                    "developer_guide_prompt", "No prompt provided."
                ),
                "claude_init_prompt": match.get("claude_init_prompt", "No init prompt provided."),
            }
            merged.append(combined)
        else:
            # We add it anyway, just without prompts
            merged.append(meta)

    return merged


def create_issue(task: dict[str, str | list[str]]):
    """Uses GitHub CLI to create an issue with rich formatting."""

    # 1. Format Title: "[P0] AH-01: Task Name"
    title = f"[{task.get('priority', 'P2')}] {task.get('task_id', '???')}: {task['task_name']}"

    # 2. Build Markdown Body
    body = f"## 📋 Overview\n{task['description']}\n\n"

    # Dependencies Section
    deps = task.get("dependencies", [])
    if deps:
        body += "## ⛓️ Dependencies\n"
        body += "> *Wait for these tasks to be completed before starting:*\n\n"
        for dep in deps:
            body += f"- [ ] **{dep}**\n"
        body += "\n"

    # AI Assistance Section (The "Beast" part)
    body += "## 🤖 AI Implementation Guide\n"
    body += "Use the prompts below to fast-track development.\n\n"

    # Developer Prompt (Dropdown)
    dev_prompt = task.get("developer_guide_prompt")
    if dev_prompt:
        body += (
            "<details>\n<summary><b>👨‍💻 Developer Guide Prompt (Cursor/Windsurf)</b></summary>\n\n"
        )
        body += "> Copy this into your AI Chat to generate the code logic.\n\n"
        body += "```text\n"
        body += dev_prompt
        body += "\n```\n</details>\n\n"

    # Init Prompt (Dropdown)
    init_prompt = task.get("claude_init_prompt")
    if init_prompt:
        body += "<details>\n<summary><b>📁 Project Init / Scaffolding Prompt (Claude Code)</b></summary>\n\n"
        body += "> Use this to generate file structures and boilerplate.\n\n"
        body += "```text\n"
        body += init_prompt
        body += "\n```\n</details>\n"

    print(f"🚀 Creating issue: {title}...")

    # 3. Execute GitHub CLI command
    try:
        subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--label",
                task.get("priority", "enhancement"),
            ],
            check=True,
            capture_output=True,
        )

        # Sleep slightly to be kind to the API
        time.sleep(1)

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create issue. Error: {e.stderr.decode()}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("📂 Loading local JSON files...")

    # 1. Load
    meta_data: list[dict[str, str | list[str]]] = load_json(file_meta_path)
    prompt_data: list[dict[str, str]] = load_json(file_prompts_path)

    # 2. Merge
    final_tasks: list[dict[str, str | list[str]]] = merge_tasks(meta_data, prompt_data)

    # 3. Confirm
    print(f"✅ Prepared {len(final_tasks)} tasks for upload.")
    confirm = input("Are you ready to upload these to GitHub? (y/n): ")

    if confirm.lower() == "y":
        for task in final_tasks:
            create_issue(task)
        print("\n✨ All tasks uploaded! Go check your GitHub Issues tab.")
    else:
        print("Operation cancelled.")
