import json
from pathlib import Path
import pandas as pd
import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1] 
RESULTS_DIR = REPO_ROOT / "results" / "k6"

st.set_page_config(page_title="Multi-Cloud k6 Test Results Viewer", layout="wide")
st.title("Results for AWS and GCP Smoke & Load Tests")

def load_results():
    rows = []
    for provider_directory in RESULTS_DIR.glob("*"):
        if not provider_directory.is_dir():
            continue
        provider = provider_directory.name
        for kind_dir in provider_directory.glob("*"):
            kind = kind_dir.name
            for results_file in kind_dir.glob("*.json"):
                try:
                    data = json.loads(results_file.read_text())
                    metrics = data.get("metrics", {})
                    duration = metrics.get("http_req_duration", {})
                    failed = metrics.get("http_req_failed", {})
                    checks = metrics.get("checks", {})


                    def ms(val):
                        return (val * 1000) if isinstance(val, (int, float)) else None
                    
                    rows.append({
                        "provider": provider,
                        "kind": kind,
                        "timestamp": results_file.stem.split("_")[-1],
                        "file": results_file.relative_to(REPO_ROOT).as_posix(),
                        "p95_ms": ms(duration.get("p(95)")),
                        "max_duration_ms": ms(duration.get("max")),
                        "avg_duration_ms": ms(duration.get("avg")),
                        "min_duration_ms": ms(duration.get("min")),
                        "failed_rate_pct": (float(failed.get("value", 0)) * 100.0),
                        "checks_passed": checks.get("passes", 0),
                        "checks_failed": checks.get("fails", 0),
                        "http_reqs": int(metrics.get("http_reqs", {}).get("count", 0)),
                    })
                except Exception:
                    pass
    return pd.DataFrame(rows)

df = load_results()
if df.empty:
    st.warning("No results found. Please run the tests first.")
    st.stop()


providers = st.multiselect("Providers", options=df["provider"].unique(), default=df["provider"].unique())
kinds = st.multiselect("Kinds", options=df["kind"].unique(), default=df["kind"].unique())
filtered = df[(df["provider"].isin(providers)) & (df["kind"].isin(kinds))].copy()

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Runs", f"{len(filtered)}")
with c2: st.metric("Avg p95 Duration (ms)", f"{filtered['p95_ms'].mean():.2f}")
with c3: st.metric("Avg Failed Rate (%)", f"{filtered['failed_rate_pct'].mean():.2f}")
with c4: st.metric("Total HTTP Reqs", f"{filtered['http_reqs'].sum()}")

st.subheader("Detailed Results")
st.dataframe(filtered.sort_values(by=["provider", "kind", "timestamp"], ascending=[True, True, True]), width='stretch')

st.subheader("Latency distribution (p95)")
st.bar_chart(filtered.set_index("file")["p95_ms"])

st.subheader("Failed rate (%) distribution")
st.bar_chart(filtered.set_index("file")["failed_rate_pct"])
