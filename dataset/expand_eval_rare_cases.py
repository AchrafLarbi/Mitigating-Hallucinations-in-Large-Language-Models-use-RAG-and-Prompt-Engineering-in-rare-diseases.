"""
Expand eval_rare_cases.jsonl by sampling diverse, high-quality cases from RDS.json.

Strategy:
  - Skip the first 150 records (already in eval_rare_cases.jsonl)
  - Select 1 case per unique diagnosis for maximum diversity
  - Filter for quality: case_report length >= 500 chars
  - Target: ~500 additional cases to bring total from 150 -> 650
  - Maintain the same format as eval_rare_cases.jsonl
"""

import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
RDS_PATH = Path(r"D:\Users\pc\OneDrive\Documents\5cp\PFE\dataset\RDS.json")
EXISTING_EVAL = DATA_DIR / "eval_rare_cases.jsonl"
OUTPUT_FILE = DATA_DIR / "eval_rare_cases.jsonl"  # will overwrite with expanded version
BACKUP_FILE = DATA_DIR / "eval_rare_cases_original_150.jsonl"

# Config
TARGET_NEW_CASES = 500
MIN_CASE_REPORT_LENGTH = 500  # minimum chars for quality
SEED = 42


def load_existing_cases():
    """Load existing 150 eval cases."""
    cases = []
    with EXISTING_EVAL.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def load_rds_records():
    """Load all RDS.json records."""
    records = []
    with RDS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def get_existing_diagnoses(existing_cases):
    """Extract diagnoses already in the eval set."""
    diagnoses = set()
    for case in existing_cases:
        target = case.get("target", "").lower().strip()
        if target:
            diagnoses.add(target)
    return diagnoses


def select_diverse_cases(rds_records, existing_diagnoses, n_target):
    """Select diverse cases: 1 per diagnosis, prioritizing quality."""
    # Group by diagnosis
    by_diagnosis = {}
    for rec in rds_records:
        diag = rec.get("diagnosis", "").lower().strip()
        if not diag:
            continue
        # Skip diagnoses already in eval set
        if diag in existing_diagnoses:
            continue
        # Quality filter
        case_report = rec.get("case_report", "")
        if len(case_report) < MIN_CASE_REPORT_LENGTH:
            continue
        if diag not in by_diagnosis:
            by_diagnosis[diag] = []
        by_diagnosis[diag].append(rec)

    print(f"  Available diagnoses (after filtering): {len(by_diagnosis)}")

    # Pick the best case per diagnosis (longest, most detailed)
    candidates = []
    for diag, recs in by_diagnosis.items():
        # Pick the one with the longest case report for quality
        best = max(recs, key=lambda r: len(r.get("case_report", "")))
        candidates.append(best)

    # Shuffle and take up to n_target
    random.seed(SEED)
    random.shuffle(candidates)
    selected = candidates[:n_target]

    print(f"  Selected {len(selected)} new cases")
    return selected


def format_as_eval_case(rds_record, case_idx):
    """Convert an RDS record to eval_rare_cases format."""
    return {
        "id": f"rds_case_{case_idx}",
        "source_dataset": "rds_case_reports",
        "split": "test",
        "task": "rare_disease_diagnosis",
        "input": {
            "question": "Analyze this clinical case report and diagnose the rare disease.",
            "case_report": rds_record.get("case_report", "")
        },
        "target": rds_record.get("diagnosis", "")
    }


def main():
    print("Loading existing eval cases...")
    existing_cases = load_existing_cases()
    print(f"  Existing cases: {len(existing_cases)}")

    existing_diagnoses = get_existing_diagnoses(existing_cases)
    print(f"  Existing unique diagnoses: {len(existing_diagnoses)}")

    print(f"\nLoading RDS.json from {RDS_PATH}...")
    rds_records = load_rds_records()
    print(f"  Total RDS records: {len(rds_records)}")

    print(f"\nSelecting {TARGET_NEW_CASES} diverse new cases...")
    new_cases = select_diverse_cases(rds_records, existing_diagnoses, TARGET_NEW_CASES)

    # Backup original file
    print(f"\nBacking up original to {BACKUP_FILE.name}...")
    import shutil
    shutil.copy2(EXISTING_EVAL, BACKUP_FILE)

    # Write expanded file
    start_idx = len(existing_cases)  # continue numbering from 150
    formatted_new = [
        format_as_eval_case(rec, start_idx + i)
        for i, rec in enumerate(new_cases)
    ]

    all_cases = existing_cases + formatted_new

    print(f"\nWriting expanded eval file: {OUTPUT_FILE.name}")
    print(f"  Original: {len(existing_cases)} cases")
    print(f"  New: {len(formatted_new)} cases")
    print(f"  Total: {len(all_cases)} cases")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for case in all_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    # Show some samples
    print("\nSample new cases:")
    for case in formatted_new[:3]:
        cr = case["input"]["case_report"]
        print(f"  {case['id']}: {case['target']} ({len(cr)} chars)")

    # Stats
    all_diags = set(c.get("target", "").lower().strip() for c in all_cases)
    print(f"\nFinal stats:")
    print(f"  Total cases: {len(all_cases)}")
    print(f"  Unique diagnoses: {len(all_diags)}")


if __name__ == "__main__":
    main()
