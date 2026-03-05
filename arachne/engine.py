"""Core Arachne engine."""

import os
import json
from datetime import datetime
from pathlib import Path
from collections import deque


def query(user_input: str, instance_root: Path) -> str:
    """Build a prompt from system info and user input, send to backend."""
    # Get basic system info
    file_structure = _get_file_structure(instance_root)
    recent_files = _get_recent_files(instance_root)
    current_time = datetime.now().isoformat()
    
    # Build the real query prompt
    real_query = f"""
System Information:
- Project Root: {instance_root}
- Current Time: {current_time}
- File Structure: {file_structure}
- Recent Files: {recent_files}

User Request: {user_input}
"""
    
    # Send to backend from config
    return _call_backend(user_input, real_query.strip(), instance_root)


def _get_file_structure(project_root: Path) -> str:
    """Get a breadth-first file structure summary."""
    try:
        files = []
        queue = deque([(project_root, 0)])  # (path, depth)

        MAX_LINES = 20
        MAX_FILES_PER_DIR = 5

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
        for root, dirs, filenames in os.walk(project_root):
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


def _call_backend(user_input: str, real_query: str, instance_root: Path) -> str:
    """Call the backend specified in .arachne/config.json."""
    import importlib
    
    config_file = instance_root / ".arachne" / "config.json"
    backend_name = "test"  # Default
    
    if config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)
            backend_name = config.get("backend", "test")
    
    # Dynamically import and call the backend
    try:
        backend_module = importlib.import_module(f"arachne.backends.{backend_name}")
        return backend_module.query(user_input, real_query)
    except (ImportError, AttributeError) as e:
        return f"Error loading backend '{backend_name}': {e}"

