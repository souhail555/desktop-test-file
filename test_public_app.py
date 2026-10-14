from app import app, generate_reply


def test_generate_reply_handles_general_questions():
    answer = generate_reply("What is Python?")
    assert isinstance(answer, str)
    assert "fallback mode" not in answer.lower()


def test_dashboard_is_accessible_without_login():
    client = app.test_client()
    response = client.get("/dashboard")
    assert response.status_code == 200
