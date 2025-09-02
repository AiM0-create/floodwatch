# Floodwatch on Render

This repo is tuned for **Render**.

## Steps
1. Push these files to a GitHub repo.
2. On https://render.com → New Web Service → **Use Docker** (auto-detected).
3. Keep defaults. Render will set `$PORT`; Docker runs Streamlit on it.
4. First run: use **India** preset, `grid_step ≥ 2°`.

### Files
- `Dockerfile` — listens on `$PORT` (Render requirement)
- `environment.yml` — conda-forge stack (prebuilt geo binaries)
- `render.yaml` — optional IaC for Render
- `app_streamlit.py`, `flood_core.py` — the app
