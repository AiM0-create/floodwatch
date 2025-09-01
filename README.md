# 🌊 Global Flood Watch — Streamlit Cloud

Sentinel-1 RTC (via STAC on Microsoft Planetary Computer) + JRC Global Surface Water (occurrence)
to flag **new water** (potential floods). Cloud-friendly and parameterized.

## Deploy on Streamlit Cloud
1. Create a new GitHub repo and upload these files.
2. On https://share.streamlit.io, click **New app**, pick your repo, and set main file to `app_streamlit.py`.
3. Deploy. First run: start with the **India** preset, `grid_step ≥ 2°`.

## Local (optional)
```bash
pip install -r requirements.txt
streamlit run app_streamlit.py
```

## Notes
- Uses public STAC (no API keys). Assets are signed automatically via `planetary_computer.sign_inplace`.
- Defaults are **Cloud-safe** (caps + caching). For global scans, consider a VM with more RAM/CPU.
