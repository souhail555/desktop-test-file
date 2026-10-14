import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

load_dotenv()

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
DB_PATH = os.path.join(os.path.dirname(__file__), "ai_agent.db")

HTML_LOGIN = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>My AI Agent</title>
  <style>
    body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #0f172a, #111827); color: white; margin: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
    .card { width: min(420px, 90vw); background: rgba(15,23,42,0.8); border: 1px solid rgba(148,163,184,0.3); border-radius: 18px; padding: 28px; box-shadow: 0 20px 40px rgba(0,0,0,0.25); }
    h1 { margin-top: 0; text-align: center; }
    form { display: flex; flex-direction: column; gap: 14px; }
    input { padding: 12px 14px; border-radius: 10px; border: 1px solid #334155; background: #0f172a; color: white; }
    button { padding: 12px 18px; border: none; border-radius: 10px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: white; font-weight: bold; cursor: pointer; }
    .note { margin-top: 12px; opacity: 0.8; font-size: 0.9rem; }
    .flash { background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4); padding: 10px; border-radius: 10px; margin-bottom: 16px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>My AI Agent</h1>
    {% if error %}<div class="flash">{{ error }}</div>{% endif %}
    <form method="post">
      <input type="text" name="username" placeholder="Your name" required>
      <button type="submit">Enter</button>
    </form>
    <div class="note">This app is public and does not require a password.</div>
  </div>
</body>
</html>
"""

HTML_DASHBOARD = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Agent</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: linear-gradient(180deg, #0b1020, #111827 30%, #0f172a);
      color: #e5e7eb;
      min-height: 100vh;
    }
    .app {
      max-width: 980px;
      margin: 0 auto;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      padding: 20px;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 18px;
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 18px;
      background: rgba(15, 23, 42, 0.7);
      box-shadow: 0 10px 30px rgba(0,0,0,0.18);
    }
    .title {
      font-size: 1.2rem;
      font-weight: bold;
    }
    .status {
      font-size: 0.75rem;
      opacity: 0.8;
    }
    .chat-shell {
      flex: 1;
      display: flex;
      flex-direction: column;
      margin-top: 20px;
      background: rgba(15, 23, 42, 0.72);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0,0,0,0.2);
    }
    .messages {
      flex: 1;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto;
      background: rgba(15,23,42,0.2);
    }
    .msg {
      max-width: 78%;
      padding: 14px 16px;
      border-radius: 18px;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .msg.user {
      align-self: flex-end;
      background: linear-gradient(135deg, #2563eb, #3b82f6);
      color: white;
      border-bottom-right-radius: 8px;
    }
    .msg.assistant {
      align-self: flex-start;
      background: rgba(30, 41, 59, 0.92);
      color: #e2e8f0;
      border: 1px solid rgba(148,163,184,0.2);
      border-bottom-left-radius: 8px;
    }
    .composer {
      border-top: 1px solid rgba(148, 163, 184, 0.2);
      padding: 16px 18px 18px;
      background: rgba(15, 23, 42, 0.8);
    }
    textarea {
      width: 100%;
      resize: none;
      min-height: 56px;
      max-height: 180px;
      padding: 15px 16px;
      border-radius: 16px;
      border: 1px solid rgba(148, 163, 184, 0.28);
      background: rgba(15, 23, 42, 0.95);
      color: #f8fafc;
      font-size: 1rem;
      outline: none;
    }
    textarea:focus {
      border-color: rgba(96, 165, 250, 0.9);
      box-shadow: 0 0 0 2px rgba(59,130,246,0.2);
    }
    .hint {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 10px;
      color: rgba(226, 232, 240, 0.8);
      font-size: 0.76rem;
    }
    @media (max-width: 640px) {
      .msg { max-width: 90%; }
      .topbar { flex-direction: column; gap: 8px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="topbar">
      <div class="title">AI Agent</div>
      <div class="status">Public mode • Live model ready</div>
    </div>

    <div class="chat-shell">
      <div class="messages" id="messages">
        <div class="msg assistant">Hello! Ask me anything and I will answer you.</div>
      </div>

      <div class="composer">
        <textarea id="prompt" rows="1" placeholder="Type a message..." aria-label="Ask the assistant"></textarea>
        <div class="hint">
          <span>Press Enter to send</span>
          <span>Shift + Enter for a new line</span>
        </div>
      </div>
    </div>
  </div>

  <script>
    const promptEl = document.getElementById('prompt');
    const messagesEl = document.getElementById('messages');

    function addMessage(role, text) {
      const div = document.createElement('div');
      div.className = 'msg ' + role;
      div.textContent = text;
      messagesEl.appendChild(div);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    promptEl.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        const value = promptEl.value.trim();
        if (!value) return;
        addMessage('user', value);
        promptEl.value = '';
        promptEl.style.height = '56px';
        fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: value })
        })
        .then(res => res.json())
        .then(data => {
          const reply = data.reply || 'I could not generate a reply.';
          addMessage('assistant', reply);
        })
        .catch(() => addMessage('assistant', 'Something went wrong. Please try again.'));
      }
    });

    promptEl.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 180) + 'px';
    });
  </script>
</body>
</html>
"""

HTML_HISTORY = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>History</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; }
    .topbar { background: #0f172a; color: white; padding: 18px 28px; display: flex; justify-content: space-between; align-items: center; }
    .nav a { color: white; text-decoration: none; margin-left: 14px; }
    .container { max-width: 900px; margin: 32px auto; padding: 0 16px; }
    .item { background: white; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 8px 18px rgba(15,23,42,0.07); }
    .role { font-weight: bold; margin-bottom: 6px; }
    .user { color: #10b981; }
    .assistant { color: #2563eb; }
    .empty { color: #64748b; }
  </style>
</head>
<body>
  <div class="topbar">
    <div><strong>My AI Agent</strong></div>
    <div class="nav">
      <a href="/dashboard">Dashboard</a>
      <a href="/logout">Logout</a>
    </div>
  </div>
  <div class="container">
    <h2>Conversation History</h2>
    {% if messages %}
      {% for msg in messages %}
        <div class="item">
          <div class="role {{ 'user' if msg.role == 'user' else 'assistant' }}">{{ msg.role.title() }}</div>
          <div>{{ msg.content }}</div>
        </div>
      {% endfor %}
    {% else %}
      <div class="empty">No conversations yet.</div>
    {% endif %}
  </div>
</body>
</html>
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def current_username():
    return session.get("username") or "guest"


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    existing = conn.execute("SELECT 1 FROM users WHERE username = ?", ("admin",)).fetchone()
    if not existing:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "admin123"))
    conn.commit()
    conn.close()


def save_message(username, role, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (username, role, content) VALUES (?, ?, ?)",
        (username, role, content),
    )
    conn.commit()
    conn.close()


def get_history(username):
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE username = ? ORDER BY id ASC",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats(username):
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    total_messages = conn.execute("SELECT COUNT(*) AS c FROM messages WHERE username = ?", (username,)).fetchone()["c"]
    last_activity = conn.execute(
        "SELECT created_at FROM messages WHERE username = ? ORDER BY id DESC LIMIT 1",
        (username,),
    ).fetchone()
    conn.close()
    return total_users, total_messages, last_activity["created_at"] if last_activity else "No activity"


def generate_reply(prompt):
    text = str(prompt or "").strip()
    if not text:
        return "Please ask a question and I will answer it."

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key)
            completion = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant. Provide concise, clear, and practical answers."},
                    {"role": "user", "content": text},
                ],
                temperature=0.7,
            )
            content = completion.choices[0].message.content
            if content:
                return content.strip()
        except Exception:
            pass

    lower = text.lower()
    if lower in {"hello", "hi", "hey", "hi there"}:
        return "Hello! I am your public AI assistant. Ask me anything and I will answer you."
    if "time" in lower:
        return f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
    if "your name" in lower:
        return "I am a public AI assistant for this app."
    if "what is ai" in lower or "what is artificial intelligence" in lower:
        return "Artificial intelligence is a field of computer science that allows machines to perform tasks that usually require human thinking, such as understanding language, recognizing patterns, and making decisions."

    return (
        f"Here is a direct answer to your question: {text}. "
        "I can help with general questions, explanations, ideas, summaries, and simple problem solving. "
        "This app is currently running in public mode without a password."
    )


@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "guest").strip() or "guest"
        session["username"] = username
        return redirect(url_for("dashboard"))
    return render_template_string(HTML_LOGIN, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    username = current_username()
    total_users, total_messages, last_activity = get_stats(username)
    return render_template_string(
        HTML_DASHBOARD,
        total_users=total_users,
        total_messages=total_messages,
        last_activity=last_activity,
    )


@app.route("/history")
def history():
    username = current_username()
    return render_template_string(HTML_HISTORY, messages=get_history(username))


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    username = current_username()
    reply = generate_reply(message)
    save_message(username, "user", message)
    save_message(username, "assistant", reply)
    return jsonify({"reply": reply})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
