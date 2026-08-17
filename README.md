# NVIDIA DGX Spark — Grafana Dashboard

> **NVIDIA DGX Spark — Throughput Without Contention v8 Output TPS Trend + NVIDIA Refined Theme**

A Grafana dashboard for monitoring an **NVIDIA DGX Spark (GB10) cluster serving vLLM** and, optionally, any small GPU box running vLLM + `node_exporter` + `nvidia_gpu_exporter`. It tracks **inference throughput and latency**, **contention around the shared KV cache / GPU**, and **raw GB10 hardware telemetry** (temperature, power, clocks, throttling) — all in an NVIDIA-green theme built for dark mode.

![schemaVersion](https://img.shields.io/badge/Grafana%20schema%20v41-classic%20v1-blueviolet)
![panels](https://img.shields.io/badge/55%20panels-vLLM%20%2B%20Node%20Exporter%20%2B%20GPU%20hardware-green)

---

## Features

### Inference / vLLM row
Cost "cloud-equivalent" calculators (Opus/Sonnet/Haiku + local electricity at ~240 W), token counters and rates, **KV cache usage**, **prefix cache hit rate**, TTFT P50/P95/P99, request hopper (running / waiting / swapped), **speculative-decode acceptance** (rate + by position), token throughput over time, prompt/output mix, request rate / success / errors, queue time, E2E request latency, TPOT / inter-token latency, engine iteration latency, prompt/output size distributions, model throughput / TTFT / queue-pressure comparisons, and HTTP latency by handler.

### Node Exporter row
Per-host load, network + disk throughput, CPU / memory / network / disk timeseries, filesystem space by mount, IOPS.

### DGX SPARK GB10 — GPU HARDWARE row
Added by [`scripts/add-gpu-hardware-panels.py`](scripts/add-gpu-hardware-panels.py) over the base vLLM dashboard, visualizing `nvidia_gpu_exporter` (`nvidia-smi`-backed) telemetry on every node:

- GPU temperature + thermal limit (`tlimit`)
- GPU power draw and utilization (%)
- Current vs max SM clock
- **Throttle bitmask** (`clocks_event_reasons_active`) — `0` = nothing active
- **Throttle counters** — seconds throttled by software power cap / software thermal / hardware thermal / hardware power brake (as rates)
- NVMe disk temperature, GPU memory / encoder utilization

---

## Requirements

| Data source | Exporters / metrics | Notes |
|---|---|---|
| **Prometheus** (datasource UID must be `prometheus`) | vLLM OpenAI server `/metrics` endpoint | Aggregated metrics like `vllm:generation_tokens_total` are expected — record rules or recorded series named `vllm:*` |
| — | `node_exporter` on each node | `node_*` and filesystem/network metrics |
| — | `nvidia_gpu_exporter` (1.x, `nvidia-smi`-backed) on port `9835` per node | Exposes `nvidia_smi_temperature_gpu`, `nvidia_smi_power_draw_watts`, `nvidia_smi_clocks_*`, `nvidia_smi_clocks_event_reasons_*`, `nvidia_smi_utilization_*`, … |
| — | Target label **`dgx_spark="true"`** | All `node_*` and `nvidia_smi_*` panels are scoped with `{dgx_spark="true"}` so the dashboard aggregates **only your DGX nodes**, not the rest of the fleet |
| — | `host_id` label | Used as the legend (`{{host_id}}`) to tell nodes apart |

### Example Prometheus scrape configuration

```yaml
# dashboard expects a datasource with uid "prometheus"
scrape_configs:
  - job_name: vllm-dgx-spark
    metrics_path: /metrics
    static_configs:
      - targets: ["192.168.10.196:8888"]   # vLLM server on the DGX head node
        labels:
          host_id: gx10-head
          dgx_spark: "true"

  - job_name: node-exporter
    file_sd_configs:
      - files: [targets/nodes.yml]          # both DGX nodes on :9100
        refresh_interval: 1m

  - job_name: gpu-exporter
    scrape_interval: 10s                    # fine-grained throttle/power sampling
    file_sd_configs:
      - files: [targets/gpu.yml]            # both DGX nodes on :9835
        refresh_interval: 1m
```

`targets/gpu.yml` example:

```yaml
- targets: ["192.168.10.196:9835"]
  labels: {host_id: gx10-head,   dgx_spark: "true"}
- targets: ["192.168.10.195:9835"]
  labels: {host_id: gx10-worker, dgx_spark: "true"}
```

Node exporters must carry the same `dgx_spark: "true"` label, e.g. via `labels` in `nodes.yml`.

> **Note on `vllm:*` metrics:** the token/throughput queries use recorded-series syntax such as `vllm:generation_tokens_total`. If your vLLM instance exposes these as plain `vllm_generation_tokens_total` counters instead, adjust the queries (a quick find-and-replace `:` → `_` and `[__rate_interval]` on counters) or add recording rules matching the `vllm:` names.

---

## Installation

The dashboard is stored as a **classic (v1) Grafana JSON** so it can be loaded by the file provider, imported via the UI, or provisioned.

### Option A — Import from the Grafana UI (quickest)

1. Grafana → **Dashboards → New → Import**
2. Paste the JSON from [`dashboards/dgx-spark-vllm.json`](dashboards/dgx-spark-vllm.json) (or drag the file in)
3. Select your Prometheus datasource for the `prometheus` UID prompt
4. Click **Import**

### Option B — Provision via the file provider

Mount the JSON into a read-only directory and reference it:

```yaml
apiVersion: 1
providers:
  - name: DGX Spark
    orgId: 1
    folder: DGX Spark
    type: file
    disableDeletion: true
    allowUiUpdates: false     # keep the repo copy authoritative
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
```

```yaml
# docker-compose.yml (grafana service)
volumes:
  - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
```

---

## GPU hardware row: reproducing / regenerating

`scripts/add-gpu-hardware-panels.py` appends the **DGX SPARK GB10 — GPU HARDWARE** row (12 timeseries + 4 stats) to the flat, classic-v1 panel list of the dashboard JSON. Run it after pulling a new upstream version of the base dashboard:

```bash
python3 scripts/add-gpu-hardware-panels.py   # edits dashboards/dgx-spark-vllm.json in place
```

It relies on the target label `dgx_spark="true"` and legends with `{{host_id}}`. Edit the `NEXT`/`Y` offsets if your dashboard JSON has different extents (it diffs cleanly against the committed file if you want to review the diff before committing).

---

## Source & attribution

- **Original base dashboard:** [`darkmatter2222/DGX_Spark_Public_Docs`](https://github.com/darkmatter2222/DGX_Spark_Public_Docs) — *NVIDIA DGX Spark — Throughput Without Contention v8 Output TPS Trend*.
- What changed here:
  - converted from Grafana v2 (declarative) to **classic v1 schema** so the file provider can load it;
  - datasource UID rewritten to `prometheus`;
  - all `node_*` panels **scoped to the `dgx_spark="true"` label** so they aggregate only the DGX nodes;
  - the **DGX SPARK GB10 — GPU HARDWARE** row added via `scripts/add-gpu-hardware-panels.py` (requires `nvidia_gpu_exporter`).

The upstream repository does not declare a license; this repository documents the modifications and does not claim ownership of the upstream panel work. The scripts and documentation in this repo are licensed under MIT (see [LICENSE](LICENSE)).

---

## Screenshots

*Coming soon* — if you use the dashboard and want to contribute a screenshot, open a PR and we'll add it here.

---

## See also

- [Grafana file provisioning docs](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/manage-dashboards/#export-and-import-dashboards)
- [vLLM metrics reference](https://docs.vllm.ai/en/latest/observability/metrics/metrics.html)
- [`nvidia_gpu_exporter`](https://github.com/utkuozdemir/nvidia_gpu_exporter) (`nvidia-smi`-based metrics)
