"""Instance resolution and initialization."""

import json
from pathlib import Path
from datetime import datetime


def find_instance_root(start: Path = None) -> Path | None:
    """Search upward for .arachne/ directory.
    
    Returns the project root (parent of .arachne/) or None if not found.
    Stop at .git/ directory (repo ceiling) or filesystem root.
    """
    if start is None:
        start = Path.cwd()
    
    current = start.resolve()
    max_depth = 25
    depth = 0
    
    while depth < max_depth:
        # Check for .arachne/
        instance_dir = current / ".arachne"
        if instance_dir.exists() and instance_dir.is_dir():
            return current
        
        # Check for .git/ (stop at repo ceiling)
        if (current / ".git").exists():
            return None
        
        # Go up one level
        parent = current.parent
        if parent == current:  # Reached filesystem root
            return None
        
        current = parent
        depth += 1
    
    return None


def check_existing_instance_in_tree(start: Path = None) -> Path | None:
    """Check if an instance already exists in the project tree.
    
    Same search as find_instance_root: goes up until .arachne/ is found,
    .git/ is hit (stop), or filesystem root is reached.
    
    Returns the root of existing instance or None if none found.
    """
    return find_instance_root(start)



def instance_dir(root: Path) -> Path:
    """Get the .arachne/ directory for a given root."""
    return root / ".arachne"


def load_config(root: Path) -> dict:
    """Load config.json from .arachne/."""
    config_file = instance_dir(root) / "config.json"
    if config_file.exists():
        with open(config_file, "r") as f:
            return json.load(f)
    return {"backend": "test"}


def init_instance(root: Path, name: str = None) -> Path:
    """Create .arachne/ with initial files."""
    arachne_dir = instance_dir(root)
    arachne_dir.mkdir(exist_ok=True)
    
    # Create config.json
    config = {
        "project_name": name or "arachne_project",
        "created_at": datetime.now().isoformat(),
        "version": 1,
        "backend": "test"
    }
    config_file = arachne_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    # Create empty history.jsonl
    (arachne_dir / "history.jsonl").touch()
    
    # Create memory.md
    (arachne_dir / "memory.md").write_text("# Project Memory\n\n")
    
    return arachne_dir
