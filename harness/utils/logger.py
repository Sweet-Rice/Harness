from harness.config import load_config


def log_thinking(thinking):
    config = load_config()
    path = config.thinking_log or "thinking.log"
    with open(path, "a") as f:
        f.write(thinking + "\n---\n")
