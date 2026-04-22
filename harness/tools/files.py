from pathlib import Path
import json


def _normalize_absolute_path(file_path: str) -> tuple[Path | None, str | None]:
    path = Path(file_path).expanduser()
    if not path.is_absolute():
        return None, f"Error: file paths must be absolute: {file_path}"
    return path, None


def read_file(file_path: str) -> str:
    """Read the contents of a file on the local machine and return its text"""
    path, error = _normalize_absolute_path(file_path)
    if error:
        return error
    if not path.exists():
        return f"Error: {file_path} does not exist"
    if not path.is_file():
        return f"Error: {file_path} is not a file"
    try:
        return path.read_text()
    except UnicodeDecodeError:
        return f"Error: {file_path} is not a UTF-8 text file"


def write_file(file_path: str, content: str) -> str:
    """Return a non-mutating write proposal for a file path."""
    path, error = _normalize_absolute_path(file_path)
    if error:
        return error

    current_content = ""
    if path.exists():
        if not path.is_file():
            return f"Error: {file_path} is not a file"
        try:
            current_content = path.read_text()
        except UnicodeDecodeError:
            return f"Error: {file_path} is not a UTF-8 text file"

    status = "create" if not path.exists() else "update"
    if current_content == content:
        return f"Write proposal for {file_path}: no changes needed"

    proposal = {
        "type": "write_proposal",
        "action": status,
        "path": str(path),
        "current_exists": path.exists(),
        "current_length": len(current_content),
        "proposed_length": len(content),
        "proposed_content": content,
        "approved": False,
        "note": "No file was written. Direct writes remain disabled until an approval flow is implemented.",
    }
    return json.dumps(proposal, indent=2)






TOOLS = [read_file, write_file]
