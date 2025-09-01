
import json
import pandas as pd
import pydeck as pdk
import streamlit as st
from flood_core import run_scan

st.set_page_config(page_title="Global Flood Watch (Sentinel-1 + JRC)", layout="wide")
st.title("🌊 Global Flood Watch — Sentinel-1 (RTC) + JRC Global Surface Water")

with st.sidebar:
    st.header("Scan parameters")
    preset = st.selectbox(
        "Region preset",
        ["India (68–98E, 6–36N)", "SE Asia (90–130E, -12–25N)", "Global (-60° to 80°)"],
        index=0
    )
    if preset.startswith("India"):
        lon_min, lon_max, lat_min, lat_max = 68, 98, 6, 36
    elif preset.startswith("SE Asia"):
        lon_min, lon_max, lat_min, lat_max = 90, 130, -12, 25
    else:
        lon_min, lon_max, lat_min, lat_max = -180, 180, -60, 80

    grid_step = st.slider("Grid size (degrees)", 0.5, 5.0, 2.0, 0.5)
    days = st.slider("Look-back days", 1, 14, 7, 1)
    st.markdown("**Water detection thresholds (dB)**")
    vv_thr = st.number_input("VV ≤", value=-18.0, step=0.5, format="%.1f")
    vh_thr = st.number_input("VH ≤", value=-27.0, step=0.5, format="%.1f")
    perm_occ = st.slider("Permanent water = occurrence ≥ (%)", 50, 100, 90, 1)
    min_km2 = st.slider("Min NEW water to alert (km²)", 1, 50, 15, 1)
    s1_res_deg = st.select_slider("S1 resolution (deg)", options=[0.00008,0.00010,0.00012,0.00015,0.00020], value=0.00012)
    max_items_per_cell = st.slider("Cap: S1 items per cell", 10, 60, 30, 5)
    max_cells = st.slider("Cap: max cells per run", 100, 2000, 800, 50)
    run_btn = st.button("🔍 Run Scan")

st.markdown(
"""This app fetches recent Sentinel‑1 RTC via the Planetary Computer STAC, detects water (VV/VH),
compares with JRC Global Surface Water occurrence, and flags cells with **new water**."""
)

@st.cache_data(show_spinner=False, ttl=3600)
def cached_scan(params_json: str):
    params = json.loads(params_json)
    df, gj = run_scan(**params)
    return df.to_dict(orient="records"), gj

if run_btn:
    params = dict(
        lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max,
        grid_step=grid_step, days=days, vv_thr=vv_thr, vh_thr=vh_thr,
        perm_occ=perm_occ, min_km2=min_km2, s1_res_deg=s1_res_deg,
        max_items_per_cell=max_items_per_cell, max_cells=max_cells
    )
    with st.spinner("Scanning…"):
        rows, gj = cached_scan(json.dumps(params, sort_keys=True))
    df = pd.DataFrame(rows)

    if df.empty:
        st.warning("No alerts for the chosen window/thresholds.")
    else:
        st.subheader(f"Alerts ({len(df)})")
        st.dataframe(df, use_container_width=True)

        st.subheader("Map")
        rows_map = [{
            "polygon": [[p["lon_min"], p["lat_min"]], [p["lon_max"], p["lat_min"]],
                        [p["lon_max"], p["lat_max"]], [p["lon_min"], p["lat_max"]]],
            "intensity": p["intensity_0to1"],
            "new_km2": p["new_water_km2"]
        } for p in gj["features"][0]["properties"]] if False else []

        layers = []
        for f in gj["features"]:
            p = f["properties"]
            xmin, ymin, xmax, ymax = p["lon_min"], p["lat_min"], p["lon_max"], p["lat_max"]
            layers.append({
                "polygon": [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]],
                "intensity": p["intensity_0to1"],
                "new_km2": p["new_water_km2"]
            })

        layer = pdk.Layer(
            "PolygonLayer",
            data=layers,
            get_polygon="polygon",
            get_elevation="new_km2",
            elevation_scale=100,
            extruded=True,
            pickable=True,
            get_fill_color="[255*intensity, 64, 128*(1-intensity), 140]",
            get_line_color=[0,0,0],
            line_width_min_pixels=1,
        )
        lat_c = (lat_min+lat_max)/2
        lon_c = (lon_min+lon_max)/2
        st.pydeck_chart(pdk.Deck(layers=[layer],
                                 initial_view_state=pdk.ViewState(latitude=lat_c, longitude=lon_c, zoom=3),
                                 tooltip={"text":"New water: {new_km2} km²\nIntensity: {intensity}"}))
        st.subheader("Download")
        st.download_button("Download CSV", data=df.to_csv(index=False).encode("utf-8"),
                           file_name="alerts.csv", mime="text/csv")
        import json as _json
        st.download_button("Download GeoJSON", data=_json.dumps(gj).encode("utf-8"),
                           file_name="alerts.geojson", mime="application/geo+json")
else:
    st.info("Adjust parameters in the sidebar and click **Run Scan**.")
