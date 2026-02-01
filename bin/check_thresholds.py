#!/usr/bin/env python
import argparse
import configparser
import json
import os
import zipfile
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse FastQC results and check against quality thresholds."
    )
    parser.add_argument("--fastqc-dir", required=True, help="Directory with FastQC .zip files")
    parser.add_argument("--config", required=True, help="INI file with QC thresholds")
    parser.add_argument("--output", required=True, help="Output JSON file with per-sample QC status")
    return parser.parse_args()


def load_thresholds(config_path: str) -> dict:
    cfg = configparser.ConfigParser()
    cfg.read(config_path)
    th = {}
    if "thresholds" in cfg:
        sec = cfg["thresholds"]
        th["min_reads"] = sec.getint("min_reads", fallback=10000)
        th["min_pct_q30"] = sec.getfloat("min_pct_q30", fallback=80.0)
        th["max_adapter_content"] = sec.getfloat("max_adapter_content", fallback=5.0)
        th["min_gc"] = sec.getfloat("min_gc", fallback=30.0)
        th["max_gc"] = sec.getfloat("max_gc", fallback=70.0)
    return th


def parse_fastqc_zip(zip_path: Path) -> dict:
    """Extract basic metrics from a FastQC .zip file.

    We rely primarily on fastqc_data.txt inside the zip.
    """
    metrics = {
        "sample": zip_path.stem.replace("_fastqc", ""),
        "total_sequences": None,
        "gc_content": None,
        "pct_q30": None,  # placeholder, may require extra parsing or approximation
        "adapter_content_max": None,
    }

    with zipfile.ZipFile(zip_path, "r") as zf:
        # fastqc_data.txt holds main stats
        data_files = [name for name in zf.namelist() if name.endswith("fastqc_data.txt")]
        if not data_files:
            return metrics
        with zf.open(data_files[0]) as fh:
            for raw_line in fh:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if line.startswith("Total Sequences"):
                    metrics["total_sequences"] = int(line.split("\t")[1])
                elif line.startswith("%GC"):
                    metrics["gc_content"] = float(line.split("\t")[1])
                # FastQC doesn't directly give %Q30; in a real pipeline you might
                # approximate it from per-base quality. Here we'll leave as None.

        # Adapter content from fastqc_data.txt "Adapter Content" section
        with zf.open(data_files[0]) as fh:
            in_adapter_section = False
            max_adapter = 0.0
            for raw_line in fh:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if line.startswith(">>Adapter Content"):
                    in_adapter_section = True
                    continue
                if in_adapter_section:
                    if line.startswith(">>END_MODULE"):
                        break
                    if line.startswith("#") or not line:
                        continue
                    parts = line.split("\t")
                    # columns: base, adapter1, adapter2, ...
                    for val in parts[1:]:
                        try:
                            max_adapter = max(max_adapter, float(val))
                        except ValueError:
                            continue
            metrics["adapter_content_max"] = max_adapter

    return metrics


def check_sample(metrics: dict, thresholds: dict) -> dict:
    reasons = []

    total = metrics.get("total_sequences")
    if total is not None and thresholds.get("min_reads") is not None:
        if total < thresholds["min_reads"]:
            reasons.append(f"total_sequences ({total}) < min_reads ({thresholds['min_reads']})")

    gc = metrics.get("gc_content")
    if gc is not None:
        min_gc = thresholds.get("min_gc")
        max_gc = thresholds.get("max_gc")
        if min_gc is not None and gc < min_gc:
            reasons.append(f"GC% ({gc}) < min_gc ({min_gc})")
        if max_gc is not None and gc > max_gc:
            reasons.append(f"GC% ({gc}) > max_gc ({max_gc})")

    adapter = metrics.get("adapter_content_max")
    if adapter is not None and thresholds.get("max_adapter_content") is not None:
        if adapter > thresholds["max_adapter_content"]:
            reasons.append(
                f"adapter_content_max ({adapter}) > max_adapter_content ({thresholds['max_adapter_content']})"
            )

    # pct_q30 left as None; you could compute it separately if needed.

    status = "PASS" if not reasons else "FAIL"
    return {
        **metrics,
        "status": status,
        "reasons": reasons,
    }


def main():
    args = parse_args()

    fastqc_dir = Path(args.fastqc_dir)
    if not fastqc_dir.is_dir():
        raise SystemExit(f"FastQC directory does not exist: {fastqc_dir}")

    thresholds = load_thresholds(args.config)

    results = {}
    for zip_file in sorted(fastqc_dir.glob("*_fastqc.zip")):
        metrics = parse_fastqc_zip(zip_file)
        if metrics["total_sequences"] is None:
            # likely invalid or incomplete FastQC output
            continue
        checked = check_sample(metrics, thresholds)
        results[checked["sample"]] = checked

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
