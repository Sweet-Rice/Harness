def log_thinking(thinking):
    with open("thinking.log", "a") as f:
        f.write(thinking + "\n---\n")
