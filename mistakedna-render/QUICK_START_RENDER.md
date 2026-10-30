# Render deployment — custom offline model

1. Upload the extracted project contents to GitHub, keeping `render.yaml` and `Dockerfile` at the repository root.
2. Include all files in `backend/app/offline_model/`, particularly the trained `weights.npz` file.
3. In Render choose **New → Blueprint** and connect the repository. Review the paid resource estimate and deploy.
4. Open the service URL, register and create a learner profile. The custom local tutor is enabled automatically.

The database URL is linked by the Blueprint. Render's port and public URL variables are read automatically. No model endpoint, model account, API key or model download is required.

The optional `OFFLINE_AI_ENABLED=false` disables the tutor. Keep `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` on a small CPU instance. Retain `DATABASE_URL` when upgrading an existing service so learning data stays intact.

“Offline model” means inference has no external AI dependency. A Render-hosted website still needs an internet connection for users to reach it. For an entirely offline installation, run the app locally after installing dependencies and building the frontend.

The included model is a custom **137,984-parameter TinyLM**, not a general-purpose large language model. It reproduces a limited set of checked lesson completions. Read `MODEL_CARD.md` before demonstrating it as AI.

## Progress report downloads

Sign in, record answers, then open **Progress → Export PDF**. Settings also offers **Markdown** for editing. No PDF service or extra environment variable is needed. Include the bundled `backend/app/assets/fonts/` directory in your repository.

The five-subject curriculum is an outline with visible question availability, not complete lesson coverage; see `CURRICULUM_COVERAGE.md`.
