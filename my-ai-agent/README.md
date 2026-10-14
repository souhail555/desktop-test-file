# My AI Agent

A beginner-friendly Python project for building a small AI agent with OpenAI support, tool execution, and a lightweight web interface.

## Features

- AI agent class with a clean fallback mode
- Optional OpenAI API integration using `OPENAI_API_KEY`
- Free local chat through Ollama (`AI_PROVIDER=ollama`)
- Built-in tools for simple arithmetic and text summarization
- Web UI to ask the agent a question
- Test suite and project structure ready for GitHub

## Project structure

```text
my-ai-agent/
├── src/
│   └── my_ai_agent/
│       ├── __init__.py
│       ├── agent.py
│       ├── config.py
│       ├── prompts.py
│       └── tools.py
├── tests/
├── examples/
├── templates/
├── static/
├── app.py
├── main.py
├── requirements.txt
├── .env.example
├── README.md
├── LICENSE
├── setup.py
├── .gitignore
└── .github/workflows/ci.yml
```

## Setup

1. Create a virtual environment:

```bash
python -m venv .venv
```

2. Activate it:

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables:

```bash
copy .env.example .env
```

Then open `.env` and set `OPENAI_API_KEY` to a secret key created on the OpenAI API keys page:

```dotenv
OPENAI_API_KEY=your_secret_key
OPENAI_MODEL=gpt-4o-mini
```

Restart the app after changing `.env`. The key stays on the server and must never be added to browser code or shared publicly. The chat header reports whether the app is connected to OpenAI or using local fallback mode. OpenAI API usage may require billing to be enabled on your account.

## Run the CLI

```bash
python main.py
```

## Run the web app

```bash
python app.py
```

Then open the browser at:

```text
http://127.0.0.1:5055/ai
```

To share a temporary public HTTPS link, start a Cloudflare Quick Tunnel after the app is running:

```powershell
cloudflared tunnel --url http://127.0.0.1:5055
```

Keep both processes running while people use the generated `trycloudflare.com` link. Quick Tunnel URLs are temporary. Chat requests are limited to 10 per minute per visitor.

### Free local model with Ollama

Install Ollama for Windows, then download a small model:

```powershell
ollama pull llama3.2:3b
```

Set `AI_PROVIDER=ollama` and `OLLAMA_MODEL=llama3.2:3b` in `.env`, then restart the app. Local inference uses your computer's resources and does not use OpenAI API credits. Set `AI_PROVIDER=openai` to switch back to OpenAI when API billing is available.

## Tools included

- `calculator`: evaluates a simple arithmetic expression
- `summarizer`: creates a short summary from text

## Example usage

```python
from my_ai_agent.agent import AIAgent

agent = AIAgent()
print(agent.respond("Explain what an AI agent is."))
print(agent.execute_tool("calculator", {"expression": "10 + 5"}))
```

## License

This project is licensed under MIT.

## GitHub-ready notes

- Keep secrets in `.env` and do not commit them.
- The CI workflow runs tests automatically on push and pull request.
- The project is ready for extension with more agents, tools, and APIs.
