import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from my_ai_agent.agent import AIAgent


def main() -> None:
    agent = AIAgent()
    prompt = "Give me a short explanation of what an AI agent is."
    print(agent.respond(prompt))


if __name__ == "__main__":
    main()
