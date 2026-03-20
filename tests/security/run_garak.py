# tests/security/run_garak.py
"""
Garak security probe runner — Financial AI endpoint
Runs configured probes; asserts ASR below gate; outputs JSON report.

Local:
  python tests/security/run_garak.py --endpoint http://localhost:1234/v1 --probes dan,encoding

CI: invoked by GitHub Actions 'security' job
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from config.settings import GATES


def run_garak(endpoint: str, probes: list[str], output_path: str, asr_threshold: float) -> dict:
    """
    Run Garak against the target endpoint.
    Returns parsed results dict with overall_asr and failed_probes.

    TODO: Replace subprocess with Garak Python API when stable:
      from garak import run as garak_run
      result = garak_run(model_type="rest", endpoint=endpoint, probes=probes)
    """
    print(f"[Garak] Running probes: {probes}")
    print(f"[Garak] Target: {endpoint}")
    print(f"[Garak] ASR Threshold: {asr_threshold}")

    # ── Hollow: replace with real Garak invocation ──────────
    # Example CLI invocation (uncomment when implementing):
    #
    # cmd = [
    #     "python", "-m", "garak",
    #     "--model-type", "rest",
    #     "--model-name", endpoint,
    #     "--probes", ",".join(probes),
    #     "--report-prefix", output_path.replace(".json", ""),
    #     "--format", "json",
    # ]
    # result = subprocess.run(cmd, capture_output=True, text=True)
    # if result.returncode != 0:
    #     print(f"[Garak] STDERR: {result.stderr}")
    #
    # Parse generated report:
    # with open(f"{output_path.replace('.json', '')}.report.json") as f:
    #     garak_output = json.load(f)

    # ── Placeholder result structure ─────────────────────────
    raise NotImplementedError(
        "run_garak: Implement Garak CLI subprocess or Python API invocation. "
        "Expected output: { 'overall_asr': float, 'failed_probes': list, 'probe_results': dict }"
    )


def main():
    parser = argparse.ArgumentParser(description="Garak Security Probe Runner")
    parser.add_argument("--endpoint",      required=True,  help="Base URL of the Financial AI app")
    parser.add_argument("--probes",        required=True,  help="Comma-separated probe names")
    parser.add_argument("--asr-threshold", type=float, default=GATES["garak_asr_max"])
    parser.add_argument("--output",        default="reports/garak_report.json")
    args = parser.parse_args()

    probe_list = [p.strip() for p in args.probes.split(",")]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    results = run_garak(args.endpoint, probe_list, args.output, args.asr_threshold)

    # Write results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    # Gate assertion
    asr = results.get("overall_asr", 1.0)
    print(f"\n[Gate] ASR: {asr:.4f} | Threshold: {args.asr_threshold}")
    if asr > args.asr_threshold:
        print(f"❌ ASR gate FAILED: {asr:.4f} > {args.asr_threshold}")
        print(f"   Failed probes: {results.get('failed_probes', [])}")
        sys.exit(1)
    else:
        print(f"✅ ASR gate PASSED: {asr:.4f} ≤ {args.asr_threshold}")
        sys.exit(0)


if __name__ == "__main__":
    main()
