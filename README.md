# Repo-convert

> Convert repository Markdown files to plain text — fully compatible with **Microsoft 365 Chat agents**.

![Repo-convert UI](https://github.com/user-attachments/assets/fc339803-4c02-4e37-a14b-5f8d87152aef)

## What it does

Repo-convert accepts a source code repository or project files and produces a cloned copy where **every `.md` file becomes a `.txt` file** with its content preserved as plain text.  The output is a new, downloadable repository that can be uploaded to environments (such as M365 Copilot agents) where `.md` files are not supported.

---

## Features

| | |
|---|---|
| ✅ Public GitHub URL | Clone and convert any public repository |
| ✅ Private GitHub URL + PAT | Authenticate with a Personal Access Token |
| ✅ ZIP upload | Upload a ZIP of any project folder |
| ✅ Download result | Download converted repo as a ZIP |
| ✅ Publish to GitHub | Push the converted repo to a new GitHub repository |
| ✅ File preview | See the before → after filename mapping |
| ✅ Collision handling | `file.md` + `file.txt` → `file.converted.txt` |
| ✅ Mixed-case extensions | `.MD`, `.Md`, `.mD` all handled |
| ✅ Binary file safety | Binary files are skipped, never corrupted |
| ✅ Original preserved | Source repository is never modified |

---

## Architecture

```
repo-convert/
├── backend/          # Python · FastAPI
│   ├── app/
│   │   ├── main.py               # ASGI app, CORS, lifespan
│   │   ├── api/routes.py         # REST endpoints
│   │   ├── models/schemas.py     # Pydantic v2 request/response models
│   │   └── services/
│   │       ├── converter.py      # Core .md → .txt logic
│   │       ├── git_service.py    # Clone / init / publish via GitPython
│   │       ├── zip_service.py    # Secure ZIP extract & create
│   │       └── job_service.py    # Background jobs (threading + TTL reaper)
│   └── tests/
│       └── test_converter.py     # 9 pytest tests for conversion logic
└── frontend/         # React · TypeScript · Create React App
    └── src/
        ├── App.tsx
        ├── components/
        │   ├── ConvertForm.tsx       # Input tabs, validation, progress bar
        │   ├── ConversionSummary.tsx # Stats, download, copy, publish buttons
        │   ├── PublishDialog.tsx     # GitHub publish modal
        │   └── FilePreview.tsx       # Before/after file mapping table
        ├── services/api.ts           # Typed fetch wrappers + 2s polling
        └── types/index.ts            # Shared TypeScript interfaces
```

### Why these libraries?

| Library | Reason |
|---|---|
| **FastAPI** | Async-capable, auto-generates OpenAPI docs, built-in multipart file upload support |
| **GitPython** | Pure-Python git operations (clone, init, add, commit, push) without subprocess shell escapes |
| **Pydantic v2** | Fast, strict request/response validation with great error messages |
| **uvicorn** | ASGI server recommended for FastAPI in production |
| **python-multipart** | Required by FastAPI for `multipart/form-data` uploads |
| **React + TypeScript** | Type-safe UI with excellent ecosystem; CRA gives zero-config setup |
| **No UI framework** | Keeps the bundle small; all styles are inline/CSS-modules |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/jobs` | Submit a conversion job (`multipart/form-data`) |
| `GET` | `/api/jobs/{id}` | Poll job status (pending → processing → completed/failed) |
| `GET` | `/api/jobs/{id}/download` | Download converted output as ZIP |
| `POST` | `/api/jobs/{id}/publish` | Publish converted repo to GitHub |
| `GET` | `/api/jobs/{id}/preview` | Before/after file mapping list |
| `GET` | `/health` | Liveness probe |
| `GET` | `/docs` | Swagger UI |

### Submit job — `POST /api/jobs`

```
Content-Type: multipart/form-data

source_type   : github_public | github_private | zip_upload
github_url    : https://github.com/owner/repo   (required for GitHub types)
github_token  : ghp_...                          (required for github_private)
file          : <binary>                         (required for zip_upload)
```

Response `202 Accepted`:
```json
{ "job_id": "550e8400-e29b-41d4-a716-446655440000", "status": "pending" }
```

### Poll status — `GET /api/jobs/{id}`

```json
{
  "job_id": "...",
  "status": "completed",
  "progress": 100,
  "summary": {
    "total_files": 42,
    "md_files_converted": 7,
    "output_repo_name": "my-repo-converted",
    "skipped_files": ["assets/logo.png"],
    "errors": []
  }
}
```

### Publish — `POST /api/jobs/{id}/publish`

```json
{
  "repo_name": "my-converted-repo",
  "github_token": "ghp_...",
  "description": "Converted with Repo-convert"
}
```

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.10 |
| Node.js | 18 |
| npm | 9 |
| git | 2.x |

---

## Local development setup

### 1 — Clone and enter the repo

```bash
git clone https://github.com/otey247/Repo-convert.git
cd Repo-convert
```

### 2 — Backend

```bash
cd backend

# (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment config
cp .env.example .env

# Start the API server (hot-reload)
uvicorn app.main:app --reload --port 8000
```

The API is now available at **http://localhost:8000**.  
Swagger UI: **http://localhost:8000/docs**

### 3 — Frontend

```bash
cd frontend

# Copy environment config
cp .env.example .env

# Install dependencies
npm install

# Start the dev server
npm start
```

The UI is now available at **http://localhost:3000**.

### 4 — Run backend tests

```bash
cd backend
pytest tests/ -v
```

---

## Environment variables

### Backend — `backend/.env`

```dotenv
PORT=8000
MAX_JOB_AGE_HOURS=1          # How long completed jobs are kept before cleanup
ALLOWED_ORIGINS=http://localhost:3000   # Comma-separated CORS origins
```

### Frontend — `frontend/.env`

```dotenv
REACT_APP_API_URL=http://localhost:8000   # Backend base URL
```

---

## Markdown conversion rules

1. Every file with a `.md` extension (any case) is renamed to `.txt` with the **same base name**.  
   `README.md` → `README.txt`
2. File **content is preserved as-is** — no HTML rendering, no stripping.
3. If a `.txt` with the same name already exists in the output folder, the converted file is named `<stem>.converted.txt` to avoid collisions.
4. All non-Markdown files are copied unchanged, including binary files such as `.docx`, `.pdf`, and images.
5. Binary files with a `.md` extension (detected via null-byte heuristic) are **skipped** to avoid producing invalid `.txt` output.
6. The source repository is **never modified**.
7. UTF-8 encoding is preserved.
8. Full directory structure is recreated in the output.

---

## Docker (optional)

```bash
# Build images
docker compose build

# Start both services
docker compose up
```

> A `docker-compose.yml` can be added — see the architecture section for the service split.

---

## Security notes

- GitHub PATs are held in memory only for the duration of the job and are **never written to logs**.
- ZIP extraction validates every member path against the destination directory to prevent path-traversal attacks.
- Temporary working directories are cleaned up after download or after `MAX_JOB_AGE_HOURS`.

---

## Assumptions

1. "Local folder" ingestion is implemented via ZIP upload (browsers cannot expose raw filesystem paths for security reasons).
2. Background jobs use Python threading — sufficient for development. For production, replace `job_service.py` with Celery + Redis.
3. GitHub publishing requires the token holder to have permission to create repositories under their own account.
4. Binary files are identified by a null-byte probe of the first 8 KB (same heuristic as `git diff`).
