"""Core Arachne engine."""

import os
import json
from datetime import datetime
from pathlib import Path
from collections import deque


def query(user_input: str, instance_root: Path) -> str:
    """Build a prompt from system info, memory, history, and user input.

    Protects core content (user request, system info, memory) from truncation.
    Only history gets shortened if prompt exceeds budget.
    """
    # Get basic system info
    file_structure = _get_file_structure(instance_root)
    recent_files = _get_recent_files(instance_root)
    current_time = datetime.now().isoformat()
    
    # Load memory (project notes)
    memory_block = _load_memory(instance_root)
    
    # Build the core/protected parts
    core_prompt = f"""
System Information:
- Project Root: {instance_root}
- Current Time: {current_time}
- File Structure: {file_structure}
- Recent Files: {recent_files}

Project Memory:
{memory_block}

User Request: {user_input}
"""
    
    # Load history and apply smart budgeting
    MAX_PROMPT_CHARS = 40000
    history_budget = MAX_PROMPT_CHARS - len(core_prompt)
    history_block = _load_history(instance_root, max_chars=max(1000, history_budget))
    
    real_query = f"""Conversation History:
{history_block}
{core_prompt}""".strip()
    
    # Final safety truncation (only if absolutely necessary)
    if len(real_query) > MAX_PROMPT_CHARS:
        # If even with history budget we're over, trim history more aggressively
        history_block = _load_history(instance_root, max_chars=500)
        real_query = f"""Conversation History:
{history_block}
{core_prompt}""".strip()
    
    # Send to backend from config
    response = _call_backend(user_input, real_query.strip(), instance_root)
    
    # Log the prompt
    _write_prompt_log(instance_root, real_query.strip())
    
    # write to history (user then assistant)
    _append_history(instance_root, "user", user_input)
    _append_history(instance_root, "assistant", response)
    
    return response


def _get_file_structure(project_root: Path) -> str:
    """Get a breadth-first file structure summary.
    
    Excludes arachne package, instance dir, and common unneeded dirs.
    """
    try:
        files = []
        queue = deque([(project_root, 0)])  # (path, depth)

        MAX_LINES = 20
        MAX_FILES_PER_DIR = 5
        SKIP_DIRS = {".arachne", "arachne", "__pycache__", ".git", ".venv", 
                     "node_modules", ".egg-info", ".pytest_cache", "venv"}

        while queue and len(files) < MAX_LINES:
            current_path, level = queue.popleft()

            indent = " " * 2 * level
            files.append(f"{indent}{current_path.name}/")

            try:
                entries = list(current_path.iterdir())
            except Exception:
                continue

            dirs = []
            filenames = []

            for entry in entries:
                if entry.is_dir():
                    if entry.name not in SKIP_DIRS:
                        dirs.append(entry)
                elif entry.is_file():
                    filenames.append(entry.name)

            # show some files
            subindent = " " * 2 * (level + 1)
            for filename in filenames[:MAX_FILES_PER_DIR]:
                if len(files) >= MAX_LINES:
                    break
                files.append(f"{subindent}{filename}")

            # enqueue directories for later (this is the BFS step)
            for d in dirs:
                queue.append((d, level + 1))

        return "\n".join(files)

    except Exception:
        return "Could not read file structure"


def _get_recent_files(project_root: Path) -> str:
    """Get recently modified files."""
    try:
        files = []
        SKIP_DIRS = {".arachne", "arachne", "__pycache__", ".git", ".venv", 
                     "node_modules", ".egg-info", ".pytest_cache", "venv"}
        
        for root, dirs, filenames in os.walk(project_root):
            # Skip excluded directories in place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            
            for filename in filenames:
                filepath = Path(root) / filename
                if filepath.stat().st_mtime > 0:  # Basic check
                    files.append((filepath, filepath.stat().st_mtime))
        
        # Sort by modification time, take top 5
        files.sort(key=lambda x: x[1], reverse=True)
        recent = [str(f[0].relative_to(project_root)) for f in files[:5]]
        return ', '.join(recent) if recent else "None found"
    except Exception:
        return "Could not determine recent files"


def _load_history(instance_root: Path, max_chars: int = 10000) -> str:
    """Return recent conversation history as a formatted string.

    Reads from .arachne/history.jsonl and concatenates the last entries
    up to a character limit.
    """
    hist_file = instance_root / ".arachne" / "history.jsonl"
    if not hist_file.exists():
        return ""
    lines = []
    try:
        with open(hist_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    role = entry.get("role", "")
                    ts = entry.get("timestamp", "")
                    content = entry.get("content", "")
                    lines.append(f"[{role} {ts}] {content}")
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping malformed history entry: {e}")
                    continue
    except Exception as e:
        print(f"Error: Failed to read history file {hist_file}: {e}")
        return ""
    text = "\n".join(lines[-20:])  # take last 20 lines
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


def _append_history(instance_root: Path, role: str, content: str) -> None:
    """Append a single message to the history file."""
    hist_file = instance_root / ".arachne" / "history.jsonl"
    hist_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content,
    }
    try:
        with open(hist_file, "a") as f:
            json.dump(entry, f)
            f.write("\n")
    except Exception as e:
        print(f"Error: Failed to append to history file {hist_file}: {e}")


def _load_memory(instance_root: Path, max_chars: int = 5000) -> str:
    """Return project memory from memory.md as a formatted string.

    Reads from .arachne/memory.md and returns up to max_chars.
    """
    mem_file = instance_root / ".arachne" / "memory.md"
    if not mem_file.exists():
        return "(No memory file)"
    try:
        content = mem_file.read_text()
        if len(content) > max_chars:
            content = content[-max_chars:]
        return content if content.strip() else "(Empty memory file)"
    except Exception as e:
        print(f"Error: Failed to read memory file {mem_file}: {e}")
        return "(Could not read memory file)"


def _write_prompt_log(instance_root: Path, real_query: str) -> None:
    """Append the full prompt to the prompts.log file."""
    log_file = instance_root / ".arachne" / "prompts.log"
    try:
        with open(log_file, "a") as f:
            f.write("\n")
            f.write(f"\n{'='*60}\n")
            f.write(f"[{datetime.now().isoformat()}]\n")
            f.write(f"{'='*60}\n")
            f.write(real_query)
            f.write("\n")
    except Exception as e:
        print(f"Error: Failed to write to prompts log {log_file}: {e}")


def _call_backend(user_input: str, real_query: str, instance_root: Path) -> str:
    """Call the backend specified in .arachne/config.json."""
    import importlib
    
    config_file = instance_root / ".arachne" / "config.json"
    backend_name = "test"  # Default
    try:
        if config_file.exists():
            with open(config_file, "r") as f:
                config = json.load(f)
                backend_name = config.get("backend", "test")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file {config_file}: {e}")
        backend_name = "test"
    except Exception as e:
        print(f"Error: Failed to read config file {config_file}: {e}")
        backend_name = "test"
    
    # Dynamically import and call the backend
    try:
        backend_module = importlib.import_module(f"arachne.backends.{backend_name}")
        return backend_module.query(user_input, real_query)
    except ImportError as e:
        return f"Error: Backend '{backend_name}' not found: {e}"
    except AttributeError as e:
        return f"Error: Backend '{backend_name}' missing query function: {e}"
    except Exception as e:
        return f"Error loading backend '{backend_name}': {e}"

