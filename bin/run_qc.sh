#!/usr/bin/env bash

set -euo pipefail

show_help() {
  cat <<EOF
  Usage: ${basename "$0"} -i <input_dir> -o <output_dir> [-t <threads>] [-c <config_file>]

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

            while getopts "i:o:t:c:h" opt; do
              case $opt in
                  i) INPUT_DIR="$OPTARG" ;;
                      o) OUTPUT_DIR="$OPTARG" ;;
                          t) THREADS="$OPTARG" ;;
                              c) CONFIG_FILE="$OPTARG" ;;
                                  h) show_help; exit 0 ;;
                                      *) echo "Unknown option: -$OPTARG" >&2; show_help; exit 1 ;;
                                        esac
                                        done

                                        # Validate input arguments
                                        if [[ -z "$INPUT_DIR" ]] || [[ -z "$OUTPUT_DIR" ]]; then
                                          echo "[ERROR] Input and output directories are required." >&2
                                            show_help
                                              exit 1
                                              fi

                                              # Set default config path if not provided
                                              if [[ -z "$CONFIG_FILE" ]]; then
                                                SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
                                                  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
                                                    CONFIG_FILE="${PROJECT_ROOT}/config/thresholds.ini"
                                                    fi

                                                    # Validate input directory exists
                                                    if [[ ! -d "$INPUT_DIR" ]]; then
                                                      echo "[ERROR] Input directory does not exist: $INPUT_DIR" >&2
                                                        exit 1
                                                        fi

                                                        # Create output subdirectories
                                                        mkdir -p "${OUTPUT_DIR}/fastqc" "${OUTPUT_DIR}/multiqc" "${OUTPUT_DIR}/qc_json"

                                                        # Find FASTQ files robustly (handles spaces in filenames)
                                                        mapfile -t FASTQ_FILES < <(find "$INPUT_DIR" -maxdepth 1 \( -name "*.fastq" -o -name "*.fastq.gz" \))

                                                        if [[ ${#FASTQ_FILES[@]} -eq 0 ]]; then
                                                          echo "[ERROR] No FASTQ files found in $INPUT_DIR" >&2
                                                            exit 1
                                                            fi

                                                            echo "[INFO] Found ${#FASTQ_FILES[@]} FASTQ files. Running FastQC with $THREADS threads..."

                                                            # Run FastQC in parallel
                                                            printf '%s\n' "${FASTQ_FILES[@]}" | xargs -P "$THREADS" -I {} bash -c 'fastqc -o "${OUTPUT_DIR}/fastqc" -t 1 "$1"' _ {}

                                                            echo "[INFO] FastQC finished. Running MultiQC..."

                                                            # Run MultiQC
                                                            multiqc "${OUTPUT_DIR}/fastqc" -o "${OUTPUT_DIR}/multiqc"

                                                            # Validate against thresholds
                                                            if [[ ! -x "$(dirname "$0")/check_thresholds.py" ]]; then
                                                              # Still allow if it's readable; Python doesn't require +x if called explicitly
                                                                if [[ ! -r "$(dirname "$0")/check_thresholds.py" ]]; then
                                                                    echo "[ERROR] check_thresholds.py not found or not readable: $(dirname "$0")/check_thresholds.py" >&2
                                                                        exit 1
                                                                          fi
                                                                          fi

                                                                          echo "[INFO] Validating QC metrics against thresholds in $CONFIG_FILE..."

                                                                          python "$(dirname "$0")/check_thresholds.py" \
                                                                            --fastqc-dir "${OUTPUT_DIR}/fastqc" \
                                                                              --config "$CONFIG_FILE" \
                                                                                --output "${OUTPUT_DIR}/qc_json/qc_summary.json"

                                                                                echo "[INFO] Pipeline completed successfully!"
