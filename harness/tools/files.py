from pathlib import Path


def read_file(file_path: str) -> str:
    """Read the contents of a file on the local machine and return its text"""
    path = Path(file_path).expanduser()
    if not path.exists():
        return f"Error: {file_path} does not exist"
    if not path.is_file():
        return f"Error: {file_path} is not a file"
    return path.read_text()


def write_file(file_path: str, content: str) -> str:
    """Write content to a file at the specified path."""
    path = Path(file_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"File written successfully to: {file_path}"






TOOLS = [read_file, write_file]
