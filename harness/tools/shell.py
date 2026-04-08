import json
import re
import shlex
import subprocess


# Read-only commands that are safe to run without user approval.
SAFE_COMMANDS = {
    "ls", "find", "tree",
    "cat", "head", "tail", "wc", "less",
    "pwd", "echo", "printf",
    "which", "whereis", "type",
    "file", "stat",
    "diff",
    "grep", "rg", "ag",
    "git",
    "date", "uname", "whoami", "hostname",
    "python", "python3",
    "pip", "uv",
    "node", "npm",
}

# Git subcommands that mutate state — block these.
GIT_MUTATING = {
    "push", "commit", "merge", "rebase", "reset", "checkout",
    "cherry-pick", "revert", "stash", "clean", "rm", "mv",
    "tag", "branch", "pull", "fetch", "clone", "init", "remote",
    "am", "apply", "format-patch", "send-email",
}

# Flags for safe commands that make them unsafe.
UNSAFE_FLAGS = {
    "rm", "rmdir",  # if somehow combined
    "--delete", "--force", "-f",
}


def _get_base_command(segment: str) -> str | None:
    """Extract the base command name from a shell segment.
    Returns None if unparseable."""
    segment = segment.strip()
    if not segment:
        return None

    # Strip leading env vars like VAR=value
    while re.match(r'^[A-Za-z_]\w*=\S*\s', segment):
        segment = re.sub(r'^[A-Za-z_]\w*=\S*\s+', '', segment, count=1)

    try:
        parts = shlex.split(segment)
    except ValueError:
        return None

    if not parts:
        return None

    return parts[0]


def _is_safe_command(segment: str) -> bool:
    """Check if a single command segment is safe to run without approval."""
    base = _get_base_command(segment)
    if base is None:
        return False

    # Reject any command not in the whitelist
    if base not in SAFE_COMMANDS:
        return False

    # Special handling for git — only allow read-only subcommands
    if base == "git":
        try:
            parts = shlex.split(segment.strip())
        except ValueError:
            return False
        # Find the subcommand (skip flags like -C)
        subcommand = None
        i = 1
        while i < len(parts):
            if parts[i].startswith("-"):
                # Skip flags and their args (e.g., -C /path)
                if parts[i] in ("-C", "-c", "--git-dir", "--work-tree"):
                    i += 2
                    continue
                i += 1
                continue
            subcommand = parts[i]
            break
        if subcommand and subcommand in GIT_MUTATING:
            return False

    # Block destructive flags on any command
    try:
        parts = shlex.split(segment.strip())
    except ValueError:
        return False

    # Check for output redirection (>, >>)
    if re.search(r'(?<![<])[>]', segment):
        return False

    return True


def _is_safe_chain(command: str) -> bool:
    """Validate that ALL commands in a chain are safe.
    Handles &&, ||, ;, and | operators."""
    # Split on chain operators: &&, ||, ;, |
    # Use regex to split while handling quoted strings
    segments = re.split(r'\s*(?:&&|\|\||\||;)\s*', command)

    if not segments:
        return False

    return all(_is_safe_command(seg) for seg in segments if seg.strip())


def _execute(command: str) -> str:
    """Execute a command and return formatted output."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=120,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        return f"Command executed: {command}\n{output}".strip()
    except subprocess.TimeoutExpired:
        return f"Command timed out after 120s: {command}"


def run_shell(command: str, intent: str, reason: str) -> str:
    """Run a bash command. Safe read-only commands execute immediately.
    Unsafe commands return a proposal requiring user approval.

    Args:
        command: The bash command to run.
        intent: What the user asked for that led to this command.
        reason: Why this specific command is needed to fulfill the intent.
    """
    if _is_safe_chain(command):
        return _execute(command)

    # Unsafe — return proposal for user approval
    display = (
        f"Intent: {intent}\n"
        f"Reason: {reason}\n"
        f"---\n"
        f"$ {command}"
    )

    return json.dumps({
        "type": "proposal",
        "shell": True,
        "command": command,
        "intent": intent,
        "reason": reason,
        "path": command,
        "diff": display,
        "content": "",
    })


TOOLS = [run_shell]
