---
title: Cloud AI Document Summarizer
emoji: 📄
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Cloud-Based AI Document Summarizer

Upload a PDF, get an AI summary, and keep a private history in the cloud.

## Architecture

```
 Browser ──► Hugging Face Space (Docker)          Supabase
             ┌───────────────────────┐   HTTPS   ┌──────────────────────┐
             │ Streamlit app         │──────────►│ Auth (email/password)│
             │ PyMuPDF  (PDF text)   │           │ Postgres (history)   │
             │ DistilBART (summaries)│           │ Storage (private PDFs)│
             └───────────────────────┘           └──────────────────────┘
                      ▲
   GitHub ── push to main ── GitHub Actions ── syncs & redeploys the Space
```

| Layer | Service | Purpose |
|---|---|---|
| Compute / hosting | Hugging Face Spaces (Docker, free CPU, 16 GB RAM) | Runs the app and the model |
| Auth | Supabase Auth | Sign up / sign in |
| Database | Supabase Postgres + Row Level Security | Per-user summary history |
| File storage | Supabase Storage (private bucket) | Optional original-PDF storage |
| CI/CD | GitHub Actions | Auto-deploy on every push |

If Supabase is not configured, the app runs in **demo mode** (summaries work, no accounts or history).

## Project structure

```
app.py            Streamlit UI (sidebar auth, Summarize + History tabs)
cloud.py          Supabase: auth, database, storage
summarizer.py     Model loading, chunking, summarization
pdf_utils.py      PDF text extraction
config.py         Settings from env vars / Streamlit secrets
supabase/schema.sql   Database tables + security policies
Dockerfile        Production image (CPU PyTorch, model baked in)
.github/workflows/    Auto-deploy to Hugging Face
```

---

## Step 1 — Set up Supabase (free)

1. Create an account at https://supabase.com and click **New project**. Save the database password somewhere.
2. Open **SQL Editor → New query**, paste the contents of `supabase/schema.sql`, and click **Run**. This creates the `summaries` table, the private `documents` bucket, and the security policies.
3. Go to **Project Settings → API** and copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon / public key** → `SUPABASE_KEY`

   Use the **anon** key only. Never put the `service_role` key in this app.
4. *(Easier testing)* **Authentication → Providers → Email**: turn off **Confirm email** while developing so new accounts can sign in immediately. Turn it back on for real use.

## Step 2 — Run locally (optional but recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit secrets.toml and paste your SUPABASE_URL and SUPABASE_KEY

python -m streamlit run app.py
```

Open http://localhost:8501, create an account, upload a PDF, and check that it appears under **History**.

## Step 3 — Push to GitHub

```bash
git init
git add .
git commit -m "Cloud AI Document Summarizer: Supabase + Docker"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/Cloud-AI-Document-Summarizer.git
git push -u origin main
```

`.streamlit/secrets.toml` is git-ignored, so your keys are not uploaded.

## Step 4 — Deploy on Hugging Face Spaces

1. Create a free account at https://huggingface.co.
2. **New → Space**. Name it (e.g. `ai-document-summarizer`), choose **Docker → Blank**, hardware **CPU basic (free)**, then **Create Space**.
3. In the Space, open **Settings → Variables and secrets** and add two **Secrets**:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
4. Get your code onto the Space. Pick one:
   - **Manual:**
     ```bash
     git remote add space https://huggingface.co/spaces/YOUR-HF-USERNAME/ai-document-summarizer
     git push space main --force
     ```
     When asked for a password, use a Hugging Face **access token** with *write* permission (Settings → Access Tokens).
   - **Automatic (recommended):** see Step 5.
5. Watch the **Logs** tab. The first build takes about 5–10 minutes (installing PyTorch and downloading the model into the image). When the status shows **Running**, your app is live at
   `https://YOUR-HF-USERNAME-ai-document-summarizer.hf.space`.

## Step 5 — Automatic deploys (CI/CD)

In your **GitHub repo → Settings → Secrets and variables → Actions**:

- **Secrets** tab → New secret: `HF_TOKEN` = your Hugging Face write token
- **Variables** tab → New variable: `HF_USERNAME` = your Hugging Face username
- **Variables** tab → New variable: `HF_SPACE` = your Space name (e.g. `ai-document-summarizer`)

From now on, every `git push` to `main` rebuilds and redeploys the Space.

## Step 6 — Test the live app

1. Open the Space URL and sign up.
2. Upload a text-based PDF → **Extract PDF Text** → **Generate AI Summary**.
3. Open the **History** tab and confirm the summary is saved. Refresh the page and sign in again to confirm it persists.
4. In Supabase **Table Editor → summaries** you can see the row, and in **Storage → documents** the stored PDF.

---

## Other hosting options

The same `Dockerfile` works anywhere that runs containers and sets `$PORT`:

- **Google Cloud Run:** `gcloud run deploy summarizer --source . --memory 4Gi --set-env-vars SUPABASE_URL=...,SUPABASE_KEY=...`
- **Render / Railway / Fly.io:** create a Docker web service from the GitHub repo and add the two environment variables. Pick an instance with at least 2 GB RAM.

Streamlit Community Cloud is **not recommended**: its memory limit is too small for PyTorch plus the model.

## Configuration

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `SUPABASE_URL` | for cloud features | – | Supabase project URL |
| `SUPABASE_KEY` | for cloud features | – | Supabase **anon** key |
| `SUPABASE_BUCKET` | no | `documents` | Storage bucket name |
| `MODEL_NAME` | no | `sshleifer/distilbart-cnn-6-6` | Any Hugging Face summarization model |
| `MAX_CHUNKS` | no | `40` | Max sections summarized per document |

## Security notes

- Row Level Security means users can only read, insert, and delete their own rows and files, even though the app uses the public anon key.
- Original PDFs are stored in a **private** bucket and shared only through 1-hour signed links.
- The Dockerfile disables Streamlit's XSRF/CORS checks, which Hugging Face's iframe embedding requires for uploads. If you host elsewhere (Cloud Run, Render), remove those two flags from the `CMD`.
- Don't upload confidential documents to a public demo.

## Known limitations

- Scanned PDFs need OCR, which is not included.
- On the free CPU tier, a long document takes a few minutes; `MAX_CHUNKS` caps the work.
- Free Spaces sleep after inactivity, so the first visit afterwards is slow to wake up.
- Reloading the browser tab signs you out (the session lives in Streamlit's per-tab state).

## Ideas for next steps

- Document question answering over the saved text
- OCR for scanned PDFs (Tesseract)
- Persistent login via cookies
- Swapping the local model for a hosted API for faster summaries
