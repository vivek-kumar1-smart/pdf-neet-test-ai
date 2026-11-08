import json, os, re, urllib.request, urllib.error
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_NAME = "PDF to NEET Test AI API"
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "100000"))
app = FastAPI(title=APP_NAME, version="0.1.0")
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

class GenerateRequest(BaseModel):
    text: str = Field(min_length=80, max_length=150000)
    exam: str = "NEET-UG"
    subject: str = "Auto-detect"
    difficulty: str = "Mixed (Basic + Moderate + Difficult)"
    count: int = Field(default=25, ge=1, le=100)

@app.get("/")
def root():
    return {"name": APP_NAME, "status": "ok", "ai_configured": bool(API_KEY), "model": MODEL}

@app.get("/health")
def health():
    return {"status": "ok", "ai_configured": bool(API_KEY), "model": MODEL}

def extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError("AI returned invalid JSON")
        return json.loads(match.group(0))

def make_prompt(req: GenerateRequest):
    return f'''You are an expert Indian entrance-exam question setter. Create exactly {req.count} original, high-quality multiple-choice questions using ONLY the source text below. Do not add facts that are not supported by the source. If the source cannot support the requested number, return fewer high-quality questions rather than inventing content.

EXAM: {req.exam}
SUBJECT: {req.subject}
DIFFICULTY: {req.difficulty}

Quality rules:
- Four options, exactly one unambiguously correct answer.
- Mix suitable question forms: direct NCERT/textbook fact, conceptual, application, statement-based, assertion-reason, matching, numerical/diagram interpretation only when source supports it.
- Keep language precise; avoid ambiguous wording, trick wording, duplicate questions, and unsupported syllabus claims.
- For NEET-UG use single-correct MCQ style. Include answer_index as zero-based integer 0-3.
- Give a concise explanation grounded in source text. Include topic and source_page where a [PAGE n] marker supports it; otherwise null.
- Ensure distractors are plausible but clearly incorrect using the source.
- Do not claim a question is guaranteed to appear in NEET.

Return ONLY valid JSON in this exact structure:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer_index":0,"explanation":"...","topic":"...","difficulty":"Moderate","source_page":2,"question_type":"Conceptual"}}]}}

SOURCE TEXT START
{req.text}
SOURCE TEXT END'''

@app.post("/api/generate")
def generate(req: GenerateRequest):
    if len(req.text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail=f"Extracted PDF text is {len(req.text)} characters; this V1 backend limit is {MAX_TEXT_CHARS}. Use a shorter PDF or split it into sections so coverage is not silently truncated.")
    if not API_KEY:
        raise HTTPException(status_code=503, detail="AI backend is not configured yet. Add GEMINI_API_KEY as a server environment variable. No payment is made by this app.")
    prompt = make_prompt(req)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.35, "responseMimeType": "application/json"}}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        raw = result["candidates"][0]["content"]["parts"][0]["text"]
        parsed = extract_json(raw)
        questions = parsed.get("questions", [])
        clean = []
        for q in questions:
            opts = q.get("options")
            ans = q.get("answer_index")
            if not isinstance(q.get("question"), str) or not isinstance(opts, list) or len(opts) != 4 or not isinstance(ans, int) or ans not in range(4):
                continue
            clean.append({"question": q["question"], "options": [str(x) for x in opts], "answer_index": ans, "explanation": str(q.get("explanation", "")), "topic": str(q.get("topic") or "General"), "difficulty": str(q.get("difficulty") or req.difficulty), "source_page": q.get("source_page") if isinstance(q.get("source_page"), int) else None, "question_type": str(q.get("question_type") or "MCQ")})
        if not clean:
            raise ValueError("No valid MCQs in AI response")
        return {"questions": clean, "requested_count": req.count, "generated_count": len(clean), "model": MODEL, "notice": "AI-generated practice questions can contain errors; verify against the source PDF and official syllabus."}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:1200]
        raise HTTPException(status_code=502, detail=f"AI provider error ({e.code}): {detail}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach AI provider: {e.reason}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Question generation failed: {str(e)}")
