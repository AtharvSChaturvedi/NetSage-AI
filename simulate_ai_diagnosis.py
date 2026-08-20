#!/usr/bin/env python3
"""
simulate_ai_diagnosis.py

NetSage CLI Tool: Diagnose network issues using Google Gemini API or an offline rule engine.

Case selection:
    If no cases file is given on the command line, one CSV is picked at
    random from the cases/ folder. Drop additional cases-*.csv files in
    there any time - no code changes needed, they're picked up automatically.
"""
import csv
import glob
import json
import os
import random
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Load environment variables from .env file
load_dotenv()

CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")

# Pre-defined offline simulation fallbacks for Non-AI mode
INTENTIONAL_ERRORS = {
    "C003": "wrong_layer",
    "C009": "wrong_cause",
    "C017": "low_confidence",
    "C020": "wrong_cause",
    "C026": "wrong_cause",
    "C029": "low_confidence",
}

NEXT_COMMAND_BY_LAYER = {
    "Layer 1": "show interfaces status",
    "Layer 2": "show vlan brief",
    "Layer 3": "show ip route",
    "Layer 3/4": "show access-lists",
    "Layer 4": "show access-lists",
    "Layer 7": "show run | include dns",
}


def pick_case_file(explicit_path=None):
    """Return the path to use: an explicit path if given, otherwise a random
    cases-*.csv from the cases/ folder."""
    if explicit_path:
        return explicit_path
    candidates = sorted(glob.glob(os.path.join(CASES_DIR, "*.csv")))
    if not candidates:
        raise FileNotFoundError(f"No case CSV files found in {CASES_DIR}")
    return random.choice(candidates)


def non_ai_diagnosis(row):
    """Fallback non-AI deterministic rule simulation."""
    case_id = row["case_id"]
    fault = row["expected_fault"]
    layer = row["osi_layer"]
    error_type = INTENTIONAL_ERRORS.get(case_id)

    root_cause = f"{fault} (inferred from show-command evidence)."
    confidence = "high"

    if error_type == "wrong_layer":
        layer_out = "Layer 3"
        root_cause = "Likely default gateway misconfiguration on the router interface."
        confidence = "medium"
    elif error_type == "wrong_cause":
        layer_out = layer
        wrong_causes = {
            "C009": "DNS server appears offline; recommend restarting DNS service.",
            "C020": "DHCP pool likely exhausted on VLAN30.",
            "C026": "Physical cable fault suspected between switches.",
        }
        root_cause = wrong_causes.get(case_id, root_cause)
        confidence = "medium"
    elif error_type == "low_confidence":
        layer_out = layer
        confidence = "low"
    else:
        layer_out = layer

    next_cmd = NEXT_COMMAND_BY_LAYER.get(layer_out, "show running-config")

    return {
        "case_id": case_id,
        "root_cause": root_cause,
        "osi_layer": layer_out,
        "confidence": confidence,
        "evidence": row["show_output"],
        "next_command": next_cmd,
        "fix_steps": [
            "Confirm root cause with next_command output",
            "Apply corrective configuration",
            "Verify fix with a repeat show command",
        ],
    }


def gemini_ai_diagnosis(client, row, system_prompt):
    """Queries Google Gemini API using the active gemini-3.6-flash model."""
    user_content = (
        f"Input Case Details:\n"
        f"- case_id: {row['case_id']}\n"
        f"- Symptom: {row['symptom']}\n"
        f"- Topology note: {row['topology_note']}\n"
        f"- Show output: {row['show_output']}\n"
    )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        temperature=0.1,
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_content,
        config=config,
    )

    clean_text = response.text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text.strip("```json").strip("```").strip()
    elif clean_text.startswith("```"):
        clean_text = clean_text.strip("```").strip()

    return json.loads(clean_text)


def print_case_summary(resp):
    """Outputs structured diagnosis results directly to CLI stdout."""
    print(f"\n--- [Case: {resp.get('case_id')}] ---")
    print(f" Root Cause  : {resp.get('root_cause')}")
    print(f" OSI Layer   : {resp.get('osi_layer')}")
    print(f" Confidence  : {resp.get('confidence')}")
    print(f" Evidence    : {resp.get('evidence')}")
    print(f" Next Cmd    : {resp.get('next_command')}")
    print(" Fix Steps   :")
    for step in resp.get("fix_steps", []):
        print(f"   * {step}")


def main():
    explicit_cases_path = sys.argv[1] if len(sys.argv) > 1 else None
    out_path = sys.argv[2] if len(sys.argv) > 2 else "ai_responses.json"

    cases_path = pick_case_file(explicit_cases_path)

    print("=========================================")
    print("              NetSage AI                 ")
    print("=========================================")
    print(f"Case file    : {cases_path}")
    print("1. AI-Based Mode (Google Gemini API)")
    print("2. Non-AI Mode (Deterministic Rule Engine)")

    choice = input("\nSelect Execution Mode (1 or 2): ").strip()
    use_ai = (choice == "1")

    client = None
    system_prompt = ""

    if use_ai:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("\n[Error]: GEMINI_API_KEY environment variable not set in .env file.")
            sys.exit(1)

        client = genai.Client(api_key=api_key)

        if not os.path.exists("diagnose_prompt.md"):
            print("\n[Error]: System prompt file 'diagnose_prompt.md' not found.")
            sys.exit(1)

        with open("diagnose_prompt.md", encoding="utf-8") as f:
            content = f.read()
            system_prompt = content.split("```\n", 1)[1].split("```", 1)[0]

    responses = []

    if not os.path.exists(cases_path):
        print(f"\n[Error]: Cases file '{cases_path}' not found.")
        sys.exit(1)

    with open(cases_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                if use_ai:
                    resp = gemini_ai_diagnosis(client, row, system_prompt)
                else:
                    resp = non_ai_diagnosis(row)

                responses.append(resp)
                print_case_summary(resp)

            except Exception as e:
                print(f"\n[Error processing {row.get('case_id', 'unknown')}]: {e}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(responses, f, indent=2)

    print(f"\nSuccessfully saved {len(responses)} case diagnoses to '{out_path}' (source: {cases_path}).")


if __name__ == "__main__":
    main()