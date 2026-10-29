# Validation — custom offline model release, 29 October 2026

## Completed

- The custom transformer was trained from random initialization on the included original corpus. No pretrained model/tokenizer/embedding was loaded. Architecture, weights, vocabulary, corpus, training log and actual generations are included.
- **20 automated tests passed**, including the existing account/privacy/quiz flows, environment loading, actual local model generation, all 40 training lesson completions, no-network inference, subject boundaries, explicit authored fallback, corrupt-weight checks and PyTorch/NumPy numerical agreement.
- **Frontend TypeScript check and Vite production build passed.**
- **Actual Uvicorn HTTP journey passed:** static frontend, health, account creation, learner profile, ten diagnostic answers, actual custom offline model response, logout/login persistence and account deletion. The test uses a temporary SQLite database and ships as `scripts/smoke_offline.py`.
- The offline API test replaces network client/connection constructors with functions that raise; tutor inference still succeeds. There is no external AI request path in the application.
- Checkpoint generated all 40 authored training completions exactly using both the PyTorch and NumPy implementations. This is a training-set memorization result, not held-out accuracy or an educational effectiveness measure.
- Training source and frozen CPU-training requirements are included separately from runtime dependencies. PyTorch is not required in the deployment image.
- Runtime-only benchmark, no PyTorch imported: model load 0.0113 seconds; mean generation 0.0627 seconds across ten Kp explanation requests; maximum 0.0733 seconds; process peak RSS 32,100 KiB. This is an inference-process benchmark in this environment, not the entire backend or a Render performance guarantee. Raw result: `training/runtime_benchmark.json`.
- `sh -n scripts/start.sh` passed. Existing schema migration is unchanged; tests migrate fresh databases using Alembic.

## Not claimed or verified

- No held-out model generalization, arbitrary question-solving or student learning improvement is claimed.
- The lexical topic router is not a learned semantic model; the completion check is a deterministic exact match, not an AI fact checker.
- Live Render deployment, a Docker image build and live PostgreSQL transport were not run here. The included GitHub Actions workflow is configured to test PostgreSQL and build Docker when you upload it.
- Browser/mobile end-to-end QA of this offline update was not performed. The optimized frontend builds and its assets/API pass automated checks.
- Missing/corrupted local weights are reported explicitly; no hosted/pretrained fallback exists.

The installed Starlette test client emits an httpx deprecation warning. Tests pass. Independent security review and educator review remain appropriate before a broad student rollout.
