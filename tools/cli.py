import json
import sys
import shlex
import subprocess
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
import typer
from rich import box
from rich.console import Console
from rich.table import Table


app = typer.Typer(help="Multi-cloud k6 test runner")
console = Console()

REPO_ROOT = Path(__file__).resolve().parents[1] if Path(__file__).name == "cli.py" and Path(__file__).parent.name == "tools" else Path(__file__).resolve().parent

AWS_DIR = REPO_ROOT / "terraform"/"aws"
GCP_DIR = REPO_ROOT / "terraform"/"gcp"  

TESTS_DIR = REPO_ROOT / "tests"/ "k6"
RESULTS_DIR = REPO_ROOT / "results"  / "k6"

SMOKE_JS = TESTS_DIR / "smoke.js"
LOAD_JS = TESTS_DIR / "load.js"


DIR_MAP = {
    "aws": AWS_DIR,
    "gcp": GCP_DIR,
}


def _check_k6() -> None:
    from shutil import which
    if which("k6") is None:
        console.print("[red]k6 is not installed or not on PATH.[/red]")
        console.print("Install it (Ubuntu) [bold] sudo apt update && sudo apt install -y k6[/bold]")
        sys.exit(1)



def _get_tf_dir(provider: str) -> Path:
    #Validates provider and returns tf dir path
    tf_dir = DIR_MAP.get(provider.lower())
    if not tf_dir:
        console.print(f"[red]Unsupported provider: {provider}[/red]")
        sys.exit(1)
    if not tf_dir.exists():
        console.print(f"[red]Terraform directory for {provider} does not exist: {tf_dir}[/red]")
        sys.exit(1)
    return tf_dir



def _terraform_output_service_url(provider: str) -> str:
   # runs 'terraform output -raw serviice_url' in the provider dir and returns the result
    tf_dir = _get_tf_dir(provider)
    cmd = ["terraform", "output", "-raw", "service_url"]
    
    try:
        out = subprocess.check_output(cmd, cwd=tf_dir, text=True).strip()
        if not out:
            raise subprocess.CalledProcessError(1, cmd, "No output from terraform")
        return out
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to read terraform output service_url in {tf_dir}[/red]")
        console.print(f"[dim]Command:[/dim] {' '.join(cmd)}")
        console.print(f"[dim]Error:[/dim] {e}")
        sys.exit(1)


def _ensure_results_dir(provider: str, kind: str) -> Path:
    # verifies and creates results dir if needed
    out_dir = RESULTS_DIR / provider.lower() / kind.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def _run_k6_test(script:Path, url: str, expect: str, provider: str, kind: str) -> Path:
    _check_k6()
    provider = provider.lower()
    out_dir = _ensure_results_dir(provider, kind)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"{kind}_{ts}.json"

    cmd = [
        "k6", "run", str(script),
        "-e", f"TARGET={url}",
        "-e", f"EXPECT_CLOUD={expect}",
        "--tag", f"provider={provider}",
        "--summary-export", str(out_file),
    ]

    console.print(f"[cyan]Running k6 {kind} test:[/cyan] [dim]")
    console.print(f"[dim]({provider}, TARGET={url}, EXPECT_CLOUD={expect})[/dim]")
    console.print(f"[dim]{' '.join(shlex.quote(c) for c in cmd)}[/dim]")

    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        console.print(f"[red]k6 test failed with exit code {proc.returncode}[/red]")
        
    return out_file

def _result_summary(json_path: Path) -> None:
    if not json_path.exists():
        console.print(f"[red]Result file does not exist: {json_path}[/red]")
        return
    
    data = json.loads(json_path.read_text())
    metrics = data.get("metrics", {})
    req_failed = metrics.get("http_req_failed", {})
    req_duration = metrics.get("http_req_duration", {})
    checks = metrics.get("checks", {})

    fail_rate_pct = float(req_failed.get("value", 0)) * 100.0
    p95 = req_duration.get("p(95)")
    checks_passed = checks.get("passes", 0)
    checks_failed = checks.get("fails", 0)

    table = Table(title=f"K6 Summary: {json_path.name}", box=box.SIMPLE_HEAVY)
    table.add_column("Metric", style="bold", no_wrap=True)
    table.add_column("Value")

    table.add_row("Fail Rate (%)", f"{fail_rate_pct:.2f}%")
    table.add_row("95th Percentile (ms)", f"{p95:.2f}" if p95 is not None else "N/A")
 
    table.add_row("Checks Passed", str(checks_passed))
    table.add_row("Checks Failed", str(checks_failed))

    console.print(table)

# logic for typer commands
def run_smoke(provider: str, url: Optional[str] = None):
    expect = provider.lower()
    target_url = url or _terraform_output_service_url(provider)
    json_path = _run_k6_test(SMOKE_JS, target_url, expect, provider, "smoke")
    _result_summary(json_path)

def run_load(provider: str, url: Optional[str] = None):
    expect = provider.lower()
    target_url = url or _terraform_output_service_url(provider)
    json_path = _run_k6_test(LOAD_JS, target_url, expect, provider, "load")
    _result_summary(json_path)

# typer commands - wrapper functions
@app.command()
def smoke(provider: str = typer.Argument(...,help="Cloud Provider"), url: Optional[str] = typer.Option(None, help= "Override service URL from terraform output")):
    # Running the smoke test
    run_smoke(provider, url)

@app.command()
def load(provider: str = typer.Argument(...,help="Cloud Provider"), url: Optional[str] = typer.Option(None, help= "Override service URL from terraform output")):
    # Running the load test
    run_load(provider, url)

@app.command()
def all():
    # Run smoke and load tests for all providers using terraform outputs
    for provider in DIR_MAP.keys():
        try:
            console.rule(f"[bold blue]Smoke Test: {provider.upper()}[/bold blue]")
            run_smoke(provider)
            console.rule(f"[bold blue]Load Test: {provider.upper()}[/bold blue]")
            run_load(provider)
        except SystemExit as e:
            console.print(f"[red]System exit while running tests for {provider}: {e}[/red]")
            
        except Exception as e:
            console.print(f"[red]Error running tests for {provider}: {e}[/red]")
            

    console.rule(f"[bold green]All tests completed[/bold green]")

@app.command()
def dashboard():
    # Launch the Streamlit dashboard to view results
    import subprocess, sys
    viewer_script = REPO_ROOT / "tools" / "viewer.py"
    console.print(f"[cyan]Launching results viewer...[/cyan]")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(viewer_script)])

if __name__ == "__main__":
    app()
    