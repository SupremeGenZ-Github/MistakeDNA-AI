# MistakeDNA AI

**Don’t just correct mistakes. Decode them.**

A CBSE learning application that helps students review mistakes, inspect possible misconceptions and practise the concepts they need to strengthen. The app includes a custom offline TinyLM trained from scratch, with its weights and training code included.

**Release:** 1.1 · **License:** [MIT](LICENSE) · **Stack:** React / TypeScript / FastAPI / SQLAlchemy

## Overview

This is the complete standalone Render application, updated to remove the external model-provider integration. It includes **a custom neural language model trained from random weights**, its tokenizer vocabulary, trained weights, original corpus, training source, inference source and measured training results. No existing pretrained model is used.

**Scope matters:** the model has 137,984 parameters and 40 curriculum lesson completions. It is a **tiny language model, not a large language model comparable to ChatGPT**. It can reproduce its narrow lesson material; it has not demonstrated general reasoning or novel question-solving. Calling it a general-purpose LLM would be misleading.

## What “offline” means

- Model inference needs no internet, API key, remote model endpoint, model account or model download.
- The inference code uses bundled NumPy weights. PyTorch is used only for optional retraining, not in the deployment image.
- The browser still needs the internet to visit an app hosted on Render. The model runs on that server.
- To use the whole application without internet, install it locally, build its frontend once and use the default local SQLite database. Initial dependency installation requires internet or an already populated package cache.
- No external AI receives student questions, answers or account data. The browser sends requests only to this app's server. PostgreSQL on Render is still a separate database service.

## GitHub repository setup

**Suggested repository name:** `mistakedna-ai`

**Repository description:**

MistakeDNA AI is a CBSE learning app with diagnostic quizzes, misconception tracking, skill maps, and a custom offline TinyLM trained from scratch. Built with React, FastAPI, and PostgreSQL, with Docker and Render deployment support. No external AI API is required.

When creating the repository, choose **Python** if GitHub asks for a `.gitignore` template. Then use the complete `.gitignore` included here, which also covers Node/Vite, virtual environments, secrets and local databases. If you upload these project files to an empty repository, you can leave GitHub's generated README/license/ignore options unchecked to avoid creating duplicate starter files.

Keep these files tracked:

- `backend/app/offline_model/weights.npz`, `manifest.json` and `corpus.json`.
- `backend/app/data/content.json` and all schema migrations.
- `frontend/package-lock.json`, `render.yaml`, `Dockerfile` and `.env.example`.

Do not commit actual `.env` files, database files, student records, `node_modules`, `.venv` or `.train-venv`. The included `.gitignore` implements these exclusions without hiding the bundled model.

## Deploy on Render

1. Extract this ZIP and upload the **contents** of `mistakedna-render/` to a GitHub repository. `render.yaml`, `Dockerfile`, `frontend/` and `backend/` must be at the root.
2. Include `backend/app/offline_model/weights.npz`, `manifest.json` and `corpus.json`. They are required runtime application assets, not files to exclude as temporary training output.
3. In Render choose **New → Blueprint**, connect the repository and review the proposed web service/database. The Blueprint uses paid resource plans; review Render's displayed estimate before creating resources.
4. Deploy. Docker compiles the frontend; the pre-deploy command applies the existing database migration. The server binds to `0.0.0.0:$PORT`.
5. Open the service URL, create an account and a learner profile. The local tutor is enabled automatically. No model credentials need to be added.

If upgrading the earlier standalone package, retain your existing Render PostgreSQL database and `DATABASE_URL`. This update does not change the schema or delete records. Deploy these files to the existing service rather than creating a replacement database. The earlier Sites prototype's data is still not automatically imported.

## Render environment variables

| Variable | Setting |
|---|---|
| `DATABASE_URL` | Linked automatically to managed PostgreSQL by `render.yaml`. Retain it on upgrades. |
| `PORT` | Render supplies it; startup reads it. |
| `RENDER_EXTERNAL_URL` | Render supplies it; becomes the origin unless `APP_ORIGIN` is set. |
| `APP_ORIGIN` | Usually unset on Render. For a custom domain set the exact HTTPS origin. |
| `APP_ENV` | `production` in Blueprint. Requires PostgreSQL, HTTPS and secure cookies. |
| `COOKIE_SECURE` | `true` on Render; `false` only for local HTTP. |
| `RUN_MIGRATIONS` | `false` in Blueprint because the pre-deploy command applies Alembic. Standalone Docker defaults to `true`. |
| `OFFLINE_AI_ENABLED` | `true` by default. Set `false` to disable only the local tutor. |
| `OFFLINE_MODEL_DIR` | Optional. Leave unset to use the bundled weights, manifest and corpus. |
| `TUTOR_REQUESTS_PER_HOUR` | `20` by default; bounds CPU generation requests per account. |
| `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` | `1` in Docker/Blueprint, keeping inference CPU work bounded. |
| `ALLOW_REGISTRATION` | `true` initially; set `false` to close new registration after provisioning a school pilot. |
| `FORWARDED_ALLOW_IPS` | `*` behind Render's ingress. Restrict it to your reverse proxy if hosting independently. |

Previously configured external-model variables are unused and can be removed from Render. No model service is substituted if the local weights are missing: the tutor reports an explicit error and quizzes continue working.

## How this custom model works

1. A disclosed lexical keyword router maps the request to one of the ten supported skills and one of four lesson modes: explain, hint, check or simpler explanation. Recent wrong answers can select a skill when the learner asks about their own mistakes. This routing is **not** a learned semantic model.
2. A custom decoder-only causal transformer generates the lesson token by token from a short structured topic/mode prompt. It starts from its bundled learned weights; it does not call another AI.
3. The completion is compared with the corresponding original authored lesson. Only an exact match is shown as **TinyLM output**. An unmatched completion is replaced by an **explicitly labeled authored fallback**; this gate is deterministic and is not neural reasoning.
4. Recorded quiz evidence is shown separately and labeled as an actual record. The model does not invent records or alter scores, XP or mastery.
5. Unsupported questions receive a clearly labeled authored scope message instead of a fabricated answer.

This design intentionally limits the tutor to checked explanations. It demonstrates a real train-from-scratch neural language model and a functional local product, but it is not broad conversational intelligence. Its low training loss reflects memorization of a small corpus. **No held-out generalization, pedagogical effectiveness or board-exam accuracy claim is made.**

The model architecture, parameter count, weights checksum and limitations are available through the signed-in `/api/model` endpoint and documented in `MODEL_CARD.md`.

## Learning features

- Standalone email/password registration, login and logout; scrypt password hashes and HTTP-only opaque session cookies.
- Private profiles and user-scoped SQL records.
- 24 original questions covering Class 11 Chemical Equilibrium and Class 10 Quadratic Equations.
- Diagnostics, rotating retests, weak-skill/prerequisite practice selection, MCQ/numerical grading, hints and explanations.
- Tentative misconception hypotheses, stored diagnosis flags and actual attempt history.
- Bayesian mastery estimates (illustrative and uncalibrated), curriculum map with zoom and concept inspection, raw scores, XP and achievements.
- Private text progress export; learning-data deletion and password-confirmed account deletion.
- Dark/light themes, reduced motion, responsive UI and error/empty/loading states.

There is still no email verification, password-recovery email, teacher/parent dashboard, flag-review interface, handwritten-answer grading, general-purpose chatbot or calibrated ML. The graph does not yet support dragging/panning. This remains a small educational MVP, not an enterprise school platform.

## Local run

Python 3.12 and Node 22.13+:

```sh
python -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
python -m alembic -c backend/alembic.ini upgrade head
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://localhost:8000. Local SQLite is stored at `data/mistakedna.db` and survives server restarts. A root `.env` file is supported; `.env.example` contains safe local defaults. Never use an ephemeral SQLite database on Render. The production configuration rejects it.

Or use Docker Compose:

```sh
cp .env.example .env
docker compose up --build
```

Compose starts PostgreSQL with a named volume and the application at http://localhost:8000. The Compose password is for local development only. `docker compose down` retains data; adding `-v` deletes it.

## Inspect or retrain your own model

All source and data are included; there are no hidden model weights.

```sh
# Use a SEPARATE training environment; PyTorch is not required to run the app.
python -m venv .train-venv
. .train-venv/bin/activate
pip install -r training/requirements.txt
OPENBLAS_NUM_THREADS=1 python training/train.py --steps 2200 --threads 2 --seed 29
```

The command builds the original corpus from `training/build_corpus.py`, creates a vocabulary from that corpus, initializes random weights, trains on CPU and exports `weights.npz`, `manifest.json` and sample generations. No pretrained tokenizer/weights are downloaded. The package installation itself needs internet initially.

The dataset is only 40 authored completions and intentionally overfits. Expanding capability requires substantially more original/appropriately licensed data, independent evaluation, longer training and a model architecture/training budget suited to the goal. More steps on these same 40 examples will not create general intelligence. After retraining, run the tests; never publish unchecked outputs merely because training loss fell.

`training/sample_generations.json` records actual greedy generations on the training prompts. It is not an unseen test set.

## Tests and schema

```sh
python -m pytest backend/tests -q
npm run build --prefix frontend
python -m alembic -c backend/alembic.ini check
```

The optional PyTorch/NumPy parity test skips when only runtime dependencies are installed. Other tests execute the actual bundled model, all 40 lesson completions, offline no-network behavior, explicit fallback, checksum failures, topic boundaries and the existing authenticated learning flows. The CI workflow runs SQLite and a disposable PostgreSQL database, then builds Docker. That supplied workflow is not represented as already having run on your repository.

Schema migrations and question IDs are preserved. Keep `backend/migrations/` checked in, back up real records before future schema changes and never edit already deployed migrations. Test database URLs must end in `_test`; the fixture resets those disposable databases.

See `VALIDATION.md` for measured results and verification limits.

## Project structure

| Location | Purpose |
|---|---|
| `frontend/` | React interface, diagnostic quizzes, knowledge map and tutor panel. |
| `backend/app/` | Authentication, learning APIs, grading, mastery and local model inference. |
| `backend/app/offline_model/` | Required custom model weights, vocabulary/manifest and original corpus. |
| `backend/migrations/` | Versioned SQL database schema. |
| `backend/tests/` | Automated account, learning and model checks. |
| `training/` | Original corpus builder, train-from-scratch code, recorded results and optional training requirements. |
| `scripts/` | Startup and local HTTP smoke test. |
| `render.yaml` | Render web service/database configuration. |
| `MODEL_CARD.md` | Model provenance, measured results and limitations. |
| `VALIDATION.md` | Checks performed and deployment/browser verification limits. |

## Contributing

Keep changes focused and include appropriate checks. Educational content needs clear explanations, stable skill/question IDs and verified answers. Model changes need transparent provenance and evaluation; training-set memorization must not be described as unseen accuracy. Keep secrets and student records out of issues, pull requests and committed files.

## License

The project's original source code, documentation, bundled original lesson corpus and custom model weights are distributed under the [MIT License](LICENSE). Third-party dependencies retain their respective licenses; this project does not relicense those dependencies or grant rights to third-party names or branding.

The model's educational and technical limitations are described in [MODEL_CARD.md](MODEL_CARD.md). The MIT license includes the standard warranty disclaimer.
