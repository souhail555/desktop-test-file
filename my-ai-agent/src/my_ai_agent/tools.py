import ast


ALLOWED_BIN_OPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Pow: "**",
    ast.Mod: "%",
}


def calculator(expression: str):
    """Safely evaluate a small arithmetic expression."""
    cleaned = expression.strip()
    tree = ast.parse(cleaned, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_BIN_OPS:
            left = _eval(node.left)
            right = _eval(node.right)
            return eval(f"{left}{ALLOWED_BIN_OPS[type(node.op)]}{right}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = _eval(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError("Unsupported expression")

    result = _eval(tree.body)
    return {"expression": cleaned, "result": str(result)}


def summarize_text(text: str) -> str:
    """Create a simple summary from a long text string."""
    sentences = [part.strip() for part in text.split(".") if part.strip()]
    if not sentences:
        return "No content to summarize."
    summary = " ".join(sentences[:2])
    return f"Summary: {summary}"


def format_response(prompt: str, answer: str) -> str:
    return f"Prompt: {prompt}\nResponse: {answer}"


def get_tool_registry():
    return {
        "calculator": calculator,
        "summarizer": summarize_text,
    }
