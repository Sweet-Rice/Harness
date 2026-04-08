import json
import difflib
from pathlib import Path


def read_file(file_path: str) -> str:
    """Read the contents of a file. Requires an absolute path (e.g. /home/user/file.txt)."""
    if not file_path.startswith("/"):
        return f"Error: file_path must be an absolute path, got: {file_path}"
    path = Path(file_path).expanduser()
    if not path.exists():
        return f"Error: {file_path} does not exist"
    if not path.is_file():
        return f"Error: {file_path} is not a file"
    return path.read_text()


def write_file(file_path: str, content: str) -> str:
    """Propose writing content to a file. Requires an absolute path. The user must approve before the write happens."""
    if not file_path.startswith("/"):
        return f"Error: file_path must be an absolute path, got: {file_path}"
    path = Path(file_path).expanduser()

    # Read existing content for diff
    if path.exists() and path.is_file():
        old_lines = path.read_text().splitlines(keepends=True)
        from_label = f"a{file_path}"
    else:
        old_lines = []
        from_label = "/dev/null"

    new_lines = content.splitlines(keepends=True)
    # Ensure trailing newline for clean diff
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    diff = "".join(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=from_label,
        tofile=f"b{file_path}",
    ))

    is_new_file = not path.exists()
    if not diff and not is_new_file:
        return "No changes — file already has this content."

    # New empty file — no diff lines, but still a creation
    if not diff:
        diff = f"+++ new file: {file_path} (empty)\n"
        command = f"touch {file_path}"
    else:
        command = f"cat <<'EOF' > {file_path}\n{content}\nEOF"

    return json.dumps({
        "type": "proposal",
        "path": str(path),
        "content": content,
        "diff": diff,
        "command": command,
    })


TOOLS = [read_file, write_file]
