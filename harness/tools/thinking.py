from harness.utils.llm import set_thinking

def enable_thinking() -> str:
    """Enable extended thinking mode for complex tasks that require deeper reasoning"""
    set_thinking(True)
    return "Thinking mode enabled"



def disable_thinking() -> str:
    """Disable extended thinking mode for simple tasks"""
    set_thinking(False)
    return "Thinking mode disabled"
TOOLS = [enable_thinking,disable_thinking]