# My AI Agent

A lightweight AI agent web app built with Flask and SQLite.

## Features
- Public access without password gate
- Dashboard view
- Chat history
- General question answering
- Optional live OpenAI integration via OPENAI_API_KEY

## Run locally
1. Create and activate a virtual environment if needed.
2. Install dependencies:
   python -m pip install -r requirements.txt
3. Start the app:
   python main.py
4. Open:
   http://127.0.0.1:5000/

## Optional AI API
Rename .env.example to .env and add an OpenAI key:

OPENAI_API_KEY=your_key_here
SECRET_KEY=your_secret_here

The app will automatically use the OpenAI API when the key is present. Without it, it still answers general questions in local mode.
