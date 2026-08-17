#!/usr/bin/env python3
"""Append DGX Spark GB10 hardware panels (temperature/power/clocks/util/throttle)
to the dgx-spark-vllm dashboard (classic v1 schema, flat panel list)."""
import json, copy

DASH = 'dashboards/dgx-spark-vllm.json'
d = json.load(open(DASH))

DS = {"type": "prometheus", "uid": "prometheus"}
NEXT = max(p["id"] for p in d["panels"]) + 1
Y = 67  # dashboard currently ends at y=67 (max y+h)

colors = {
    "green":  "#76B900",   # NVIDIA green
    "teal":   "#1DB2A4",
    "orange": "#FFA500",
    "red":    "#E02F44",
    "yellow": "#FFCC00",
    "blue":   "#3274D9",
}

BASE_TS = {
    "type": "timeseries",
    "datasource": DS,
    "links": [],
    "transforms": [],
    "fieldConfig": {
        "defaults": {
            "color": {"mode": "palette-classic"},
            "custom": {
                "axisBorderShow": False, "axisCenteredZero": False,
                "axisColorMode": "text", "axisLabel": "", "axisPlacement": "auto",
                "barAlignment": 0, "barWidthFactor": 0.6, "drawStyle": "line",
                "fillOpacity": 10, "gradientMode": "opacity",
                "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                "insertNulls": False, "lineInterpolation": "smooth",
                "lineWidth": 2, "pointSize": 4, "scaleDistribution": {"type": "linear"},
                "showPoints": "never", "showValues": False, "spanNulls": True,
                "stacking": {"group": "A", "mode": "none"},
                "thresholdsStyle": {"mode": "off"}
            },
            "noValue": "\u2014",
            "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": 0}]}
        },
        "overrides": []
    },
    "options": {
        "annotations": {"clustering": -1, "multiLane": False},
        "legend": {"calcs": ["lastNotNull", "mean", "max"], "displayMode": "table",
                   "enableFacetedFilter": False, "overflow": "ellipsis",
                   "placement": "bottom", "showLegend": True},
        "tooltip": {"hideZeros": False, "mode": "single", "sort": "none"}
    }
}

BASE_STAT = {
    "type": "stat",
    "datasource": DS,
    "links": [],
    "transforms": [],
    "fieldConfig": {
        "defaults": {
            "color": {"mode": "thresholds"},
            "thresholds": {"mode": "absolute", "steps": [
                {"color": "#76B900", "value": None},
                {"color": "#FFA500", "value": 70},
                {"color": "#E02F44", "value": 85},
            ]},
            "noValue": "\u2014",
            "unit": "celsius",
            "mappings": []
        },
        "overrides": []
    },
    "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "textMode": "auto",
        "showPercentChange": False
    }
}

def target(expr, legend, color=None):
    t = {"expr": expr, "refId": "A" if color is None else "B",
         "legendFormat": legend, "editorMode": "code", "range": True}
    if color:
        t["refId"] = "B"
    return t

def node_legend(label):
    """Legend showing host_id for both nodes."""
    return "{{host_id}}"

def panel(p):
    return {"id": p["id"], "gridPos": p["gridPos"], "type": p["type"],
            "title": p["title"], "datasource": DS, "targets": p["targets"],
            "fieldConfig": p["fieldConfig"], "options": p["options"]}

panels_out = []

def new_row(y):
    return {"id": 90000, "type": "row", "title": "DGX SPARK GB10 — GPU HARDWARE (nvidia_gpu_exporter)",
            "collapsed": False, "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
            "panels": []}

def new_ts(title, expr, legend, unit, grid, color=None, extra=None):
    p = copy.deepcopy(BASE_TS)
    p.update({"id": NEXT, "title": title, "gridPos": {"h": grid[0], "w": grid[1], "x": grid[2], "y": grid[3]}})
    t = target(expr, legend, color)
    t["refId"] = "A"
    p["targets"] = [t]
    p["fieldConfig"]["defaults"]["unit"] = unit
    return p

def new_ts_multi(title, targets_, unit, grid):
    p = copy.deepcopy(BASE_TS)
    p.update({"id": NEXT, "title": title, "gridPos": {"h": grid[0], "w": grid[1], "x": grid[2], "y": grid[3]}})
    p["targets"] = []
    for i, (expr, legend) in enumerate(targets_):
        t = target(expr, legend)
        t["refId"] = chr(ord("A") + i)
        p["targets"].append(t)
    p["fieldConfig"]["defaults"]["unit"] = unit
    return p

def new_stat(title, expr, unit, grid, thresholds=None, mappings=None):
    p = copy.deepcopy(BASE_STAT)
    p.update({"id": NEXT, "title": title, "gridPos": {"h": grid[0], "w": grid[1], "x": grid[2], "y": grid[3]}})
    p["targets"] = [target(expr, node_legend(None))]
    p["targets"][0]["refId"] = "A"
    p["fieldConfig"]["defaults"]["unit"] = unit
    if thresholds:
        p["fieldConfig"]["defaults"]["thresholds"] = {"mode": "absolute", "steps": thresholds}
    return p

# ---- Row header ----
NEXT += 1
row = new_row(Y)
Y += 1

# -- Row 1: headline stats (temperature, tlimit, power, utilization) --
# GPU temp (per node)
NEXT += 1; p = new_stat("GPU TEMPERATURE (°C)", 'nvidia_smi_temperature_gpu{dgx_spark="true"}', "celsius", [6, 6, 0, Y], thresholds=[{"color": "#76B900","value": None},{"color":"#FFA500","value": 70},{"color":"#E02F44","value": 85}]); panels_out.append(p)
NEXT += 1; p = new_stat("GPU THERMAL LIMIT TLIMIT", 'nvidia_smi_temperature_gpu_tlimit{dgx_spark="true"}', "celsius", [6, 6, 6, Y]); panels_out.append(p)
NEXT += 1; p = new_stat("GPU POWER (W)", 'nvidia_smi_power_draw_watts{dgx_spark="true"}', "watt", [6, 6, 12, Y]); panels_out.append(p)
NEXT += 1; p = new_stat("GPU UTILIZATION (%)", 'nvidia_smi_utilization_gpu_ratio{dgx_spark="true"} * 100', "percent", [6, 6, 18, Y]); panels_out.append(p)
Y += 6

# -- Row 2: temperature & power over time --
NEXT += 1; p = new_ts("GPU TEMPERATURE OVER TIME", 'nvidia_smi_temperature_gpu{dgx_spark="true"}', "{{host_id}}", "celsius", [7, 12, 0, Y]); panels_out.append(p)
NEXT += 1; p = new_ts("GPU TLIMIT INCREASE (60°C+ → throttling risk)", 'nvidia_smi_temperature_gpu_tlimit{dgx_spark="true"}', "{{host_id}}", "celsius", [7, 12, 12, Y]); panels_out.append(p)
Y += 7

# -- Row 3: clocks & utilization --
NEXT += 1; p = new_ts_multi("SM CLOCK: CURRENT vs MAX (GHz)", [
    ('nvidia_smi_clocks_current_sm_clock_hz{dgx_spark="true"} / 1e9', "{{host_id}} current"),
    ('nvidia_smi_clocks_max_sm_clock_hz{dgx_spark="true"} / 1e9', "{{host_id}} max"),
], "hertz", [7, 12, 0, Y]); panels_out.append(p)

# Add per-node color overrides so current != max visually
p["fieldConfig"]["overrides"] = [
    {"matcher": {"id": "byRegexp", "options": "/current/"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "#1DB2A4"}}]},
    {"matcher": {"id": "byRegexp", "options": "/max/"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "#E02F44"}}]}
]

NEXT += 1; p = new_ts_multi("GPU UTILIZATION (DECODE BATCH %) OVER TIME", [
    ('nvidia_smi_utilization_gpu_ratio{dgx_spark="true"} * 100', "{{host_id}}"),
], "percent", [7, 12, 12, Y]); panels_out.append(p)
Y += 7

# -- Row 4: throttle active + throttle counters --
NEXT += 1; p = new_ts("CLOCK THROTTLE ACTIVE (bitmask, 0 = none)", 'nvidia_smi_clocks_event_reasons_active{dgx_spark="true"}', "{{host_id}}", "short", [7, 12, 0, Y]); panels_out.append(p)
NEXT += 1; p = new_ts_multi("THROTTLE COUNTERS: TIME THROTTLED (sec/min)", [
    ('rate(nvidia_smi_clocks_event_reasons_counters_sw_power_cap_seconds{dgx_spark="true"}[$__rate_interval])', "{{host_id}} sw power cap"),
    ('rate(nvidia_smi_clocks_event_reasons_counters_sw_thermal_slowdown_seconds{dgx_spark="true"}[$__rate_interval])', "{{host_id}} sw thermal"),
    ('rate(nvidia_smi_clocks_event_reasons_counters_hw_thermal_slowdown_seconds{dgx_spark="true"}[$__rate_interval])', "{{host_id}} hw thermal"),
    ('rate(nvidia_smi_clocks_event_reasons_counters_hw_power_brake_slowdown_seconds{dgx_spark="true"}[$__rate_interval])', "{{host_id}} hw power brake"),
], "s", [7, 12, 12, Y]); panels_out.append(p)
Y += 7

# -- Row 5: NVMe + memory util --
NEXT += 1; p = new_ts_multi("NVME DISK TEMPERATURE", [
    ('node_hwmon_temp_celsius{chip="nvme_nvme0", dgx_spark="true"}', "{{host_id}} nvme"),
], "celsius", [6, 12, 0, Y]); panels_out.append(p)
NEXT += 1; p = new_ts_multi("GPU MEMORY / ENCODER UTILIZATION", [
    ('nvidia_smi_utilization_memory_ratio{dgx_spark="true"} * 100', "{{host_id}} mem"),
    ('nvidia_smi_utilization_encoder_ratio{dgx_spark="true"} * 100', "{{host_id}} enc"),
], "percent", [6, 12, 12, Y]); panels_out.append(p)
Y += 6

# Assign row.panels and append to dashboard
d["panels"].extend([row] + panels_out)
json.dump(d, open(DASH, "w"), indent=2)
print(f"appended {len(panels_out)} hardware panels + 1 row to {DASH}; new max y={Y}")
