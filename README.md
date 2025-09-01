# 🌊 Global Flood Watch — Streamlit Cloud (Python 3.11)

**Fix for your install errors:** Streamlit Cloud was using Python 3.13, which lacks wheels for Rasterio/PyProj.
This repo pins Python via `.streamlit/runtime.txt` to **3.11** and uses wheel-friendly package versions.

## Deploy
1) Push these files to a GitHub repo.  
2) On Streamlit Cloud → New app → main file: `app_streamlit.py`.  
3) First run: choose **India** preset and keep `grid_step ≥ 2°`.

## Local
```bash
pip install -r requirements.txt
streamlit run app_streamlit.py
```
