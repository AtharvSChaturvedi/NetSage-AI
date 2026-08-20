# NetSage AI — Applied AI + Network Troubleshooting

An AI-assisted troubleshooter for Cisco-style Packet Tracer labs. It reads
symptoms and show-command output, proposes a likely fault, OSI layer, next
command, and evidence-backed fix — but **never applies a fix without human
review**.

## Contents

| File | Purpose |
|---|---|
| `cases/` | Folder of case CSVs (`cases.csv`, `cases-02.csv`, ...). Each run picks one file at random — drop in new `cases-NN.csv` files any time, no code changes needed. |
| `diagnose_prompt.md` | System prompt + JSON output schema + 3 worked examples for the AI diagnosis step |
| `rule_checker.py` | Deterministic Python checks (duplicate IPs, wrong masks, interface down, VLAN/trunk issues, missing routes) — an independent, non-AI signal |
| `simulate_ai_diagnosis.py` | CLI tool. Picks a random case file from `cases/`, then either calls the Google Gemini API (mode 1) or a deterministic offline fallback (mode 2), and saves output to `ai_responses.json` |
| `ai_responses.json` | Saved AI diagnosis for the most recently processed case file |
| `human_review_log.csv` | Reviewer verdict (Accepted / Edited / Rejected) + notes per case |
| `responsible_ai_log.md` | Detailed write-up of cases where the AI was corrected, and the pattern behind the mistakes |
| `requirements.txt` | Python dependencies (`google-genai`, `python-dotenv`) |

## Setup

```bash
pip install -r requirements.txt
```

For AI mode, create a `.env` file in the project root with:
```
GEMINI_API_KEY=your_key_here
```

## How to run it

```bash
# 1. Run the deterministic rule checker (random case file from cases/)
python3 rule_checker.py

#    ...or check a specific file:
python3 rule_checker.py cases/cases.csv

# 2. Run AI diagnosis (also randomly picks a case file from cases/)
python3 simulate_ai_diagnosis.py
#    Then choose:
#      1 = Google Gemini API (needs GEMINI_API_KEY)
#      2 = Non-AI deterministic fallback (no key needed)

#    ...or target a specific file and output path:
python3 simulate_ai_diagnosis.py cases/cases-02.csv ai_responses.json
```

## Adding more cases

Drop any new `cases-NN.csv` file into `cases/` — it must keep the same
columns as the existing files:

```
case_id,symptom,topology_note,show_output,expected_fault,osi_layer,concept_tag,severity
```

Both `rule_checker.py` and `simulate_ai_diagnosis.py` scan the folder and
pick a file at random on every run, so new cases are picked up automatically.

## Workflow (matches the assignment's step-by-step)

1. **Cases** — `cases/`, currently 60 cases (C001–C060) split across two files, covering VLAN, gateway, DHCP, DNS, routing, ACL, NAT, wireless, STP, VTP, GRE, and port-security faults.
2. **Prompts** — `diagnose_prompt.md`, forces JSON with `root_cause`, `confidence`, `evidence`, `next_command`, `fix_steps`.
3. **Rule checker** — `rule_checker.py`, independent deterministic pass.
4. **AI diagnosis** — `simulate_ai_diagnosis.py` → `ai_responses.json`.
5. **Human review** — `human_review_log.csv`, every case marked Accepted / Edited / Rejected; corrected cases detailed in `responsible_ai_log.md`.

## Current results snapshot

- 60 cases logged across two case files in `cases/`, each with full evidence
- Rule checker independently flags fault-relevant cases on deterministic signals alone (varies by which file is picked)
- 5+ documented Responsible-AI corrections — see `responsible_ai_log.md`

## Suggested demo script (5–10 min)

1. Show a broken case in Packet Tracer (pick one from `cases/`, e.g. C001 VLAN misassignment).
2. Run `simulate_ai_diagnosis.py` — show the AI's JSON output for that case.
3. Show the reviewer's entry in `human_review_log.csv` for that case.
4. Apply the fix in Packet Tracer, re-run the `next_command`, and verify.# NetSage-AI
