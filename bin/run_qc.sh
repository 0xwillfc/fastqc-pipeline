#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<EOF
Usage: $(basename "$0") -i <input_dir> -o <output_dir> [-t <threads>] [-c <config_file>] [-h]

Runs FastQC on all FASTQ(.gz) files in the input directory, summarizes with MultiQC,
then validates results against quality thresholds.

Options:
  -i  Input directory containing *.fastq or *.fastq.gz
  -o  Output directory for FastQC/MultiQC results
  -t  Number of threads (default: 4)
  -c  Threshold config (INI) file (default: config/thresholds.ini relative to project root)
  -h  Show this help message
EOF
}

INPUT_DIR=""
OUTPUT_DIR=""
THREADS=4
CONFIG_FILE=""

while getopts ":i:o:t:c:h" opt; do
  case "$opt" in
    i) INPUT_DIR="$OPTARG" ;;
    o) OUTPUT_DIR="$OPTARG" ;;
    t) THREADS="$OPTARG" ;;
    c) CONFIG_FILE="$OPTARG" ;;
    h) show_help; exit 0 ;;
    \?) echo "[ERROR] Unknown option: -$OPTARG" >&2; show_help; exit 1 ;;
    :)  echo "[ERROR] Option -$OPTARG requires an argument." >&2; show_help; exit 1 ;;
  esac
done

# Validate input arguments
if [[ -z "$INPUT_DIR" || -z "$OUTPUT_DIR" ]]; then
  echo "[ERROR] Input and output directories are required." >&2
  show_help
  exit 1
fi

# Validate threads
if ! [[ "$THREADS" =~ ^[0-9]+$ ]] || [[ "$THREADS" -lt 1 ]]; then
  echo "[ERROR] Threads (-t) must be a positive integer. Got: $THREADS" >&2
  exit 1
fi

# Validate input directory exists
if [[ ! -d "$INPUT_DIR" ]]; then
  echo "[ERROR] Input directory does not exist: $INPUT_DIR" >&2
  exit 1
fi

# Set default config path if not provided
if [[ -z "$CONFIG_FILE" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  CONFIG_FILE="${PROJECT_ROOT}/config/thresholds.ini"
fi

if [[ ! -r "$CONFIG_FILE" ]]; then
  echo "[ERROR] Config file not found or not readable: $CONFIG_FILE" >&2
  exit 1
fi

# Create output subdirectories
mkdir -p "${OUTPUT_DIR}/fastqc" "${OUTPUT_DIR}/multiqc" "${OUTPUT_DIR}/qc_json"

# Find FASTQ files robustly (handles spaces/newlines)
mapfile -d '' -t FASTQ_FILES < <(find "$INPUT_DIR" -maxdepth 1 -type f \( -name "*.fastq" -o -name "*.fastq.gz" \) -print0)

if [[ ${#FASTQ_FILES[@]} -eq 0 ]]; then
  echo "[ERROR] No FASTQ files found in $INPUT_DIR" >&2
  exit 1
fi

echo "[INFO] Found ${#FASTQ_FILES[@]} FASTQ files. Running FastQC with $THREADS threads..."

# Run FastQC in parallel; export OUTPUT_DIR so subshells see it
export OUTPUT_DIR
printf '%s\0' "${FASTQ_FILES[@]}" | xargs -0 -n 1 -P "$THREADS" bash -lc 'fastqc -o "${OUTPUT_DIR}/fastqc" -t 1 "$1"' _

echo "[INFO] FastQC finished. Running MultiQC..."
multiqc "${OUTPUT_DIR}/fastqc" -o "${OUTPUT_DIR}/multiqc"

# Validate against thresholds
CHECKER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_thresholds.py"
if [[ ! -r "$CHECKER" ]]; then
  echo "[ERROR] check_thresholds.py not found or not readable: $CHECKER" >&2
  exit 1
fi

echo "[INFO] Validating QC metrics against thresholds in $CONFIG_FILE..."
python "$CHECKER" \
  --fastqc-dir "${OUTPUT_DIR}/fastqc" \
  --config "$CONFIG_FILE" \
  --output "${OUTPUT_DIR}/qc_json/qc_summary.json"

echo "[INFO] Pipeline completed successfully!"
