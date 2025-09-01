
# 🌊 Global Flood Watch — Docker app (Streamlit)

Streamlit Cloud had geo wheels issues. This repo uses **Conda (conda-forge)** inside Docker,
so `rasterio/pyproj/geopandas` install cleanly anywhere.

## Option A — Run locally with Docker
```bash
docker build -t floodwatch .
docker run -p 8501:8501 floodwatch
# open http://localhost:8501
```

## Option B — Deploy to Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/floodwatch
gcloud run deploy floodwatch --image gcr.io/PROJECT_ID/floodwatch --platform managed --region asia-south1 --allow-unauthenticated
```

## Option C — Deploy to Render (free tier)
- Connect repo at https://render.com
- Choose **Docker** and leave defaults, or use `render.yaml` in this repo.

## Option D — Railway / Fly.io / EC2
Any Docker host works:
- Railway: New Project → Deploy from repo (Dockerfile auto-detected)
- Fly.io: `fly launch` then `fly deploy`

## Why Docker + conda-forge?
Geospatial libs need GDAL/PROJ. The conda-forge stack ships prebuilt binaries,
so no compilation headaches.

### Notes
- Public STAC; no secrets needed.
- Start with **India** preset and `grid_step ≥ 2°`.
- Increase resources for larger/global scans.
