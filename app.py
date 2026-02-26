import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # loads .env locally (in prod, use real env vars)

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
MODEL_NAME = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")  # default to your preference

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SYSTEM_PROMPT = """
You are "Torque", an expert auto mechanic and diagnostic advisor.

Mission:
- Give practical, safe, step-by-step advice.
- Ask 3–6 clarifying questions when required.
- Provide likely causes + quick checks + what to do next.
- Provide cost/urgency guidance, and when to stop driving.

Safety rules:
- If the issue could be unsafe (brakes, steering, fuel smell, overheating, airbag light, oil pressure),
  strongly recommend stopping and getting professional help.
- Never suggest bypassing safety systems or emissions equipment.
- If user asks for something illegal or dangerous, refuse and offer safer alternatives.

Output format (always):
1) Quick summary (2–3 lines)
2) Key questions (bulleted)
3) Most likely causes (ranked)
4) Step-by-step checks (easy → advanced)
5) Recommended fix options (DIY vs mechanic)
6) Urgency & “Is it safe to drive?”
7) Rough cost ranges (mention depends on make/model/location)
"""

def build_user_prompt(user_text: str) -> str:
    # You can enrich this further (e.g., force them to provide make/model/year)
    return f"""
Customer question:
{user_text}

Important: If the user didn't provide car details, ask for:
- Make / model / year / engine (petrol/diesel/hybrid/EV)
- Odometer
- Symptoms (when it happens, any warning lights, smells, sounds)
- Recent work done
- Location/climate (optional)
"""

@app.get("/health")
def health():
    ok = bool(GROQ_API_KEY)
    return jsonify({
        "status": "ok" if ok else "missing_key",
        "has_key": ok,
        "model": MODEL_NAME
    }), 200 if ok else 500


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/ask")
def ask():
    if not client:
        return jsonify({"error": "GROQ_API_KEY missing. Set it as an environment variable."}), 500

    data = request.get_json(silent=True) or {}
    user_question = (data.get("question") or "").strip()

    if not user_question:
        return jsonify({"error": "Please enter a question."}), 400

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(user_question)},
    ]

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,  # your requested model: openai/gpt-oss-120b
            messages=messages,
            temperature=0.3,
            max_tokens=900,
        )

        answer = resp.choices[0].message.content
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"Groq call failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)