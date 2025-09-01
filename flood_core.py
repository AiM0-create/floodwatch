# flood_core.py
import json, datetime as dt
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import shapely.geometry as sgeom

import rioxarray  # noqa
from rasterio.enums import Resampling

from pystac_client import Client
import planetary_computer
import stackstac

PLANETARY_COMPUTER_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
S1_COLLECTION = "sentinel-1-rtc"
JRC_COLLECTION = "jrc-gsw"
EQUAL_AREA_CRS = "EPSG:6933"

# -----------------------
# Helpers
# -----------------------

def date_range_str(days_back: int) -> str:
    end = dt.datetime.utcnow().replace(microsecond=0)
    start = end - dt.timedelta(days=days_back)
    return f"{start.isoformat()}/{end.isoformat()}"

def generate_grid(lon_min: float, lon_max: float, lat_min: float, lat_max: float,
                  step_deg: float) -> List[sgeom.Polygon]:
    polys = []
    lon = lon_min
    while lon < lon_max:
        lat = lat_min
        while lat < lat_max:
            ll = (lon, lat)
            ur = (min(lon + step_deg, lon_max), min(lat + step_deg, lat_max))
            polys.append(sgeom.box(ll[0], ll[1], ur[0], ur[1]))
            lat += step_deg
        lon += step_deg
    return polys

def to_db(linear: xr.DataArray, eps: float = 1e-6) -> xr.DataArray:
    return 10.0 * xr.apply_ufunc(np.log10, xr.where(linear > eps, linear, eps))

def open_pc_client() -> Client:
    return Client.open(PLANETARY_COMPUTER_STAC, modifier=planetary_computer.sign_inplace)

# -----------------------
# STAC queries
# -----------------------

def search_s1_items(client: Client, geom_geojson: dict, dt_str: str, max_items: int = 40):
    return list(client.search(
        collections=[S1_COLLECTION],
        intersects=geom_geojson,
        datetime=dt_str,
        query={"s1:instrument_mode": {"eq": "IW"}},
        max_items=max_items,
    ).get_items())

def stack_s1(items, resolution=0.00012):
    if not items: return None
    available = set(items[0].assets.keys())
    assets = [a for a in ("VV", "VH") if a in available]
    if not assets:
        assets = [k for k in available if k.upper() in ("VV", "VH", "HH", "HV")]
        if not assets: return None

    return stackstac.stack(
        items, assets=assets, chunksize=2048, epsg=4326, resolution=resolution,
        resampling=Resampling.bilinear,
    )  # dims: time,y,x,band

def fetch_jrc_occurrence(client: Client, geom_geojson: dict) -> Optional[xr.DataArray]:
    items = list(client.search(
        collections=[JRC_COLLECTION],
        intersects=geom_geojson,
        max_items=50
    ).get_items())
    if not items: return None
    chosen, asset_key = None, None
    for it in items:
        for k in it.assets.keys():
            if "occurrence" in k.lower():
                chosen, asset_key = it, k; break
        if chosen: break
    if not chosen: return None

    da = stackstac.stack([chosen], assets=[asset_key], chunksize=2048, epsg=4326,
                         resampling=Resampling.nearest)
    if "time" in da.dims: da = da.isel(time=0)
    if "band" in da.dims: da = da.isel(band=0)
    da.name = "jrc_occurrence"
    return da

# -----------------------
# Water / area
# -----------------------

def s1_water_mask(s1_da: xr.DataArray,
                  vv_thr_db=-18.0, vh_thr_db=-27.0) -> xr.DataArray:
    """Tuned thresholds for mountainous/forested areas: a bit stricter."""
    med = s1_da.median(dim="time", skipna=True)
    bands = list(med.band.values.astype(str))
    vv = med.sel(band="VV") if "VV" in bands else None
    vh = med.sel(band="VH") if "VH" in bands else None

    vv_db = to_db(vv) if vv is not None else None
    vh_db = to_db(vh) if vh is not None else None

    if vv_db is not None and vh_db is not None:
        water = (vv_db <= vv_thr_db) & (vh_db <= vh_thr_db)
    elif vv_db is not None:
        water = (vv_db <= vv_thr_db)
    elif vh_db is not None:
        water = (vh_db <= vh_thr_db)
    else:
        water = xr.zeros_like(med.isel(band=0), dtype=bool)

    return water.fillna(False).rename("water_now")

def reproject_match_equal_area(src: xr.DataArray, ref: xr.DataArray):
    ref_eq = ref.rio.write_crs(4326, inplace=False).rio.reproject(EQUAL_AREA_CRS, resampling=Resampling.nearest)
    src_eq = src.rio.write_crs(4326, inplace=False).rio.reproject_match(ref_eq, resampling=Resampling.nearest)
    return src_eq, ref_eq

def pixel_area_km2(da_eq: xr.DataArray) -> float:
    transform = da_eq.rio.transform()
    px_area_m2 = abs(transform.a * transform.e)
    return px_area_m2 / 1e6

# -----------------------
# Analysis
# -----------------------

def analyze_cell(client: Client,
                 cell_geom: sgeom.base.BaseGeometry,
                 dt_str: str,
                 vv_thr_db: float,
                 vh_thr_db: float,
                 perm_occ_thresh: int,
                 min_km2: float,
                 s1_res_deg: float = 0.00012,
                 max_items_per_cell: int = 40) -> Optional[Dict]:
    geom_geojson = json.loads(gpd.GeoSeries([cell_geom], crs=4326).to_json())["features"][0]["geometry"]

    s1_items = search_s1_items(client, geom_geojson, dt_str, max_items=max_items_per_cell)
    if not s1_items: return None

    s1_stack = stack_s1(s1_items, resolution=s1_res_deg)
    if s1_stack is None: return None

    water_now = s1_water_mask(s1_stack, vv_thr_db=vv_thr_db, vh_thr_db=vh_thr_db)

    jrc_occ = fetch_jrc_occurrence(client, geom_geojson)
    if jrc_occ is None: return None

    water_eq, jrc_eq = reproject_match_equal_area(water_now, jrc_occ)
    perm = (jrc_eq >= perm_occ_thresh).fillna(False)

    new_water = (water_eq.astype(bool) & (~perm.astype(bool))).fillna(False)

    # dask-aware sums
    def _sum(a: xr.DataArray) -> float:
        if hasattr(a.data, "compute"):
            return float(a.sum().compute())
        return float(a.sum().item())

    px_km2 = pixel_area_km2(new_water)
    new_km2 = _sum(new_water) * px_km2
    perm_km2 = _sum(perm) * px_km2
    water_km2 = _sum(water_eq) * px_km2

    if new_km2 < min_km2:
        return None

    intensity = 0.0 if water_km2 == 0 else max(0.0, min(1.0, new_km2 / max(water_km2, 1e-6)))
    lon_min, lat_min, lon_max, lat_max = cell_geom.bounds
    return {
        "lon_min": lon_min, "lat_min": lat_min, "lon_max": lon_max, "lat_max": lat_max,
        "new_water_km2": round(new_km2, 3),
        "perm_water_km2": round(perm_km2, 3),
        "total_water_km2": round(water_km2, 3),
        "intensity_0to1": round(intensity, 3),
        "datetime_window_utc": dt_str,
        "vv_thr_db": vv_thr_db,
        "vh_thr_db": vh_thr_db,
        "perm_occurrence_threshold": perm_occ_thresh,
    }

def run_scan(lon_min=-180, lon_max=180, lat_min=-60, lat_max=80,
             grid_step=2.0, days=7,
             vv_thr=-18.0, vh_thr=-27.0, perm_occ=90, min_km2=15.0,
             s1_res_deg=0.00012, max_items_per_cell=40, max_cells=None):
    """
    Tuned defaults:
      - days=7 (sparser acquisitions)
      - stricter VV/VH thresholds
      - min_km2=15 to reduce noise
      - ~12–13 m res for speed (0.00012 deg)
      - caps for Streamlit Cloud
    """
    client = open_pc_client()
    dt_str = date_range_str(days)
    grid = generate_grid(lon_min, lon_max, lat_min, lat_max, grid_step)
    if max_cells is not None and len(grid) > max_cells:
        grid = grid[:max_cells]

    alerts, features = [], []
    for cell in grid:
        try:
            res = analyze_cell(client, cell, dt_str, vv_thr, vh_thr, perm_occ,
                               min_km2, s1_res_deg, max_items_per_cell)
            if res:
                alerts.append(res)
                features.append({
                    "type": "Feature",
                    "geometry": sgeom.mapping(cell),
                    "properties": res
                })
        except Exception:
            continue

    df = pd.DataFrame(alerts).sort_values(["new_water_km2"], ascending=False) if alerts else pd.DataFrame()
    gj = {"type": "FeatureCollection", "features": features}
    return df, gj
