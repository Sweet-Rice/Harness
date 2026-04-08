


def ping(message: str) -> str:
    """Echo a message back to confirm the server is working"""
    return f"pong: {message}"


TOOLS = [ping]