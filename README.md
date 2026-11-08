# PDF → NEET Test AI (V1 starter)

A free-first PWA prototype that extracts selectable PDF text in the browser, asks a separately hosted backend to generate MCQs, runs a timed test, and saves test papers/results in the browser's IndexedDB.

## What is implemented
- Responsive dark-mode PWA UI; manifest allows any orientation.
- Browser-side PDF text extraction with PDF.js.
- AI generation API adapter for Gemini; API key stays on the backend.
- Test interface with timer, +4/−1/0 scoring, answer review and explanations.
- Local test history in IndexedDB.
- No payment, checkout, subscription or auto-billing code.
- PDF file itself is not uploaded; extracted text is sent only after the user confirms consent and presses Generate.

## Important V1 limitations
- Scanned/image-only PDFs need OCR; not included in this first version.
- Very large PDFs may exceed the model context / configured text cap. The backend currently clips at `MAX_TEXT_CHARS`; do not treat clipped coverage as complete.
- The current AI adapter expects a Gemini API key. Free-tier availability, model access, quotas and pricing are controlled by Google and can change. This app does not guarantee unlimited free AI calls.
- Questions are AI-generated practice material and must be checked against the source and current official exam syllabus.
- Public multi-user release needs authentication, rate limits, abuse controls and per-user storage before launch.

## Run locally

### 1. Start backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set GEMINI_API_KEY in your shell or hosting environment (not in frontend files)
export GEMINI_API_KEY="your-key"
uvicorn main:app --reload --port 8000
```

On Windows PowerShell use `$env:GEMINI_API_KEY="your-key"` before running uvicorn.

### 2. Serve frontend

From the project root, run:

```bash
python -m http.server 5500
```

Open `http://localhost:5500`, set AI backend URL to `http://127.0.0.1:8000`, select a PDF, confirm the text-sharing notice in Settings, and generate a test.

## Deploy
- Frontend: publish the project root to GitHub Pages (HTTPS).
- Backend: deploy `backend/` using its Dockerfile to a backend host that supports Python containers. Set `GEMINI_API_KEY` as a secret environment variable. Free hosting may sleep or have usage limits.
- After deployment, paste the backend HTTPS URL into the app's AI backend URL field.
- For production, replace `ALLOWED_ORIGINS=*` with the exact frontend origin.

## GitHub Pages upload
Upload the contents of the project root (not the enclosing folder) to the root of your repository. The frontend files are `index.html`, `manifest.webmanifest`, `sw.js`, and `icon.svg`. The backend is deployed separately; GitHub Pages cannot run Python/FastAPI.

## Privacy
This prototype does not persist the original PDF on the backend. It extracts text locally, then sends extracted text to the AI backend only after consent and explicit generation. The AI provider may process the submitted text under its own terms. Do not upload confidential, copyrighted, or personal documents unless you have the right to do so and understand the provider's data policy.
