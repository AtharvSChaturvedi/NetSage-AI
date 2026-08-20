#!/usr/bin/env python3
"""
rule_checker.py
Deterministic (non-AI) checks for common Cisco config mistakes.
Runs independently of the AI diagnosis, so results can be cross-checked
against the AI's output (evidence-backed, reproducible, no hallucination risk).

Case selection:
    If no path is given, one CSV is picked at random from the cases/ folder
    (drop more cases-*.csv files in there any time — no code changes needed).
    Pass an explicit path to check a specific file instead.

Usage:
    python3 rule_checker.py                # random file from cases/
    python3 rule_checker.py cases/cases.csv  # a specific file
"""
import csv
import glob
import os
import random
import re
import sys
from collections import defaultdict

CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")

RULES = []


def rule(name):
    def deco(fn):
        RULES.append((name, fn))
        return fn
    return deco


@rule("duplicate_ip")
def check_duplicate_ip(show_output, symptom):
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", show_output)
    if "duplicate" in symptom.lower() or "conflict" in symptom.lower():
        return True, f"Possible duplicate IP referenced: {ips}"
    return False, None


@rule("wrong_mask")
def check_wrong_mask(show_output, symptom):
    m = re.search(r"255\.255\.0\.0", show_output)
    if m and "mask" not in symptom.lower():
        return True, "Unusual /16 mask found where a /24 access subnet is expected"
    if "mask" in symptom.lower() or "wrong subnet mask" in show_output.lower():
        return True, "Subnet mask mismatch indicated by evidence"
    return False, None


@rule("gateway_mismatch")
def check_gateway_mismatch(show_output, symptom):
    if "gateway" in symptom.lower() and re.search(r"gateway\s+192\.168\.\d+\.\d+", show_output):
        m = re.findall(r"192\.168\.\d+\.\d+", show_output)
        if len(set(m)) > 1:
            return True, f"Multiple differing gateway addresses referenced: {set(m)}"
    return False, None


@rule("interface_down")
def check_interface_down(show_output, symptom):
    if re.search(r"notconnect|administratively down|line protocol down|err-disable", show_output, re.I):
        return True, "Interface state flagged as down / err-disabled in evidence"
    return False, None


@rule("missing_vlan")
def check_missing_vlan(show_output, symptom):
    if re.search(r"VLAN\s*\d+.*not (in|allowed)|assigned to VLAN 1", show_output, re.I):
        return True, "VLAN assignment or trunk-allowed-list issue detected"
    return False, None


@rule("missing_route")
def check_missing_route(show_output, symptom):
    if re.search(r"no route|missing.*route|route to.*missing|gateway of last resort is not set", show_output, re.I):
        return True, "Routing table missing an expected destination network"
    return False, None


def pick_case_file(explicit_path=None):
    """Return the path to use: an explicit path if given, otherwise a random
    cases-*.csv from the cases/ folder."""
    if explicit_path:
        return explicit_path
    candidates = sorted(glob.glob(os.path.join(CASES_DIR, "*.csv")))
    if not candidates:
        raise FileNotFoundError(f"No case CSV files found in {CASES_DIR}")
    return random.choice(candidates)


def run(cases_path):
    results = []
    counts = defaultdict(int)
    with open(cases_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            case_id = row["case_id"]
            show_output = row["show_output"]
            symptom = row["symptom"]
            hits = []
            for name, fn in RULES:
                triggered, detail = fn(show_output, symptom)
                if triggered:
                    hits.append((name, detail))
                    counts[name] += 1
            results.append((case_id, hits))
    return results, counts


def main():
    explicit_path = sys.argv[1] if len(sys.argv) > 1 else None
    cases_path = pick_case_file(explicit_path)
    print(f"Using case file: {cases_path}\n")

    results, counts = run(cases_path)

    print("=== Rule Checker Report ===")
    for case_id, hits in results:
        if hits:
            print(f"\n{case_id}:")
            for name, detail in hits:
                print(f"  [{name}] {detail}")

    print("\n=== Summary: rule trigger counts ===")
    for name, _ in RULES:
        print(f"  {name}: {counts.get(name, 0)}")

    flagged = sum(1 for _, hits in results if hits)
    print(f"\nTotal cases: {len(results)} | Cases flagged by >=1 deterministic rule: {flagged}")


if __name__ == "__main__":
    main()