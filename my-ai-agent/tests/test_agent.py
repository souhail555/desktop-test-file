import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx import Document
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import app as app_module
from app import app, extract_uploaded_text
from my_ai_agent.agent import AIAgent


def test_agent_returns_string_response(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "local")
    agent = AIAgent()
    response = agent.respond("Hello")
    assert isinstance(response, str)
    assert len(response) > 0


def test_agent_reports_openai_authentication_errors(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")

    class AuthenticationError(Exception):
        pass

    def reject_request(**kwargs):
        raise AuthenticationError("invalid key")

    agent = AIAgent()
    agent.client = SimpleNamespace(responses=SimpleNamespace(create=reject_request))
    with pytest.raises(RuntimeError, match="rejected the API key"):
        agent.respond("Hello")


def test_agent_uses_ollama_chat_api(monkeypatch):
    import my_ai_agent.agent as agent_module

    class FakeClient:
        def __init__(self, **kwargs):
            self.base_url = kwargs["base_url"]
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **options: SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Local answer"))]
            )))

    monkeypatch.setattr(agent_module, "OpenAI", FakeClient)
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    agent = AIAgent()

    assert agent.provider == "ollama"
    assert agent.model == "llama3.2:3b"
    assert agent.client.base_url == "http://127.0.0.1:11434/v1"
    assert agent.respond("Hello") == "Local answer"


def test_agent_streams_ollama_response(monkeypatch):
    import my_ai_agent.agent as agent_module

    class FakeClient:
        def __init__(self, **kwargs):
            def create(**options):
                assert options["stream"] is True
                return iter([
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Fast "))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="reply"))]),
                ])

            self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

    monkeypatch.setattr(agent_module, "OpenAI", FakeClient)
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    agent = AIAgent()

    assert "".join(agent.respond_stream("Hello")) == "Fast reply"


def test_extract_uploaded_txt_and_docx():
    assert extract_uploaded_text("notes.txt", b"  A plain text note  ") == "A plain text note"

    document = Document()
    document.add_paragraph("DOCX note content")
    buffer = io.BytesIO()
    document.save(buffer)
    assert extract_uploaded_text("notes.docx", buffer.getvalue()) == "DOCX note content"


def test_extract_uploaded_rejects_empty_pdf_and_unsupported_files():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    with pytest.raises(ValueError, match="لم أجد نصاً"):
        extract_uploaded_text("empty.pdf", buffer.getvalue())
    with pytest.raises(ValueError, match="الأنواع المدعومة"):
        extract_uploaded_text("script.exe", b"not allowed")


def test_chat_reads_uploaded_txt_file(monkeypatch):
    seen_prompts = []

    def fake_respond(agent, prompt, model=None):
        seen_prompts.append(prompt)
        return "Read the attached text"

    monkeypatch.setattr(AIAgent, "respond", fake_respond)
    response = app.test_client().post(
        "/api/chat",
        data={
            "prompt": "Summarize this",
            "model": "llama3.2:3b",
            "files": (io.BytesIO("Arabic file text".encode()), "notes.txt"),
        },
        content_type="multipart/form-data",
        headers={"CF-Connecting-IP": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert response.get_json()["files"] == ["notes.txt"]
    assert "Arabic file text" in seen_prompts[0]
    assert "Summarize this" in seen_prompts[0]


def test_chat_streams_ollama_response(monkeypatch):
    class StreamingAgent:
        provider = "ollama"
        client = object()
        model = "llama3.2:3b"

        def respond_stream(self, prompt, model=None):
            yield "First "
            yield "token"

    monkeypatch.setattr(app_module, "AIAgent", StreamingAgent)
    client = app_module.create_app().test_client()
    response = client.post(
        "/api/chat",
        data={"prompt": "Hello", "stream": "1"},
        content_type="multipart/form-data",
        headers={"CF-Connecting-IP": "192.0.2.20"},
    )

    assert response.mimetype == "text/event-stream"
    assert '"token": "First "' in response.get_data(as_text=True)
    assert '"done": true' in response.get_data(as_text=True)


def test_chat_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(AIAgent, "respond", lambda agent, prompt, model=None: "OK")
    client = app.test_client()

    responses = [
        client.post(
            "/api/chat",
            json={"prompt": "Hello"},
            headers={"CF-Connecting-IP": "192.0.2.11"},
        )
        for _ in range(11)
    ]

    assert all(response.status_code == 200 for response in responses[:10])
    assert responses[10].status_code == 429


def test_agent_uses_default_system_prompt():
    agent = AIAgent()
    assert agent.system_prompt
    assert "assistant" in agent.system_prompt.lower()


def test_agent_supports_tool_execution():
    agent = AIAgent()
    result = agent.execute_tool("calculator", {"expression": "2 + 2"})
    assert "4" in str(result)


def test_review_code_includes_review_comment():
    review = AIAgent().review_code("print('hi')")
    assert "Review" in review or "review" in review.lower()


def test_health_route_works():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"


def test_api_status_reports_connection_mode():
    response = app.test_client().get("/api/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] in {"openai", "ollama", "local"}
    assert isinstance(payload["connected"], bool)


def test_chat_route_validates_input():
    client = app.test_client()
    response = client.post("/api/chat", json={}, headers={"CF-Connecting-IP": "192.0.2.12"})
    assert response.status_code == 400
    payload = response.get_json()
    assert "error" in payload


def test_login_page_renders():
    client = app.test_client()
    response = client.get("/login")
    assert response.status_code == 200


def test_dashboard_is_public():
    client = app.test_client()
    response = client.get("/dashboard")
    assert response.status_code == 200


def test_history_route_works_for_guest_user():
    client = app.test_client()
    response = client.get("/history")
    assert response.status_code == 200
