# Responsible AI Log — NetSage AI

The AI assistant never applies a fix on its own. Every diagnosis is reviewed
by a human as **Accepted**, **Edited**, or **Rejected**. Below are the cases
where the AI's output needed correction, why, and what the reviewer changed.

| Case | AI said | What was actually wrong | Verdict | Why |
|---|---|---|---|---|
| C003 | Layer 3 gateway misconfiguration | Missing `encapsulation dot1Q 10` on the router sub-interface (Layer 2) | Edited | The AI matched a surface symptom ("gateway unreachable") to the most common cause instead of reading the sub-interface config evidence carefully. Reviewer corrected `osi_layer` and `root_cause`. |
| C007 | Missing DNS option in DHCP pool (correct) | Fix was right but incomplete | Edited | AI's `fix_steps` didn't include client-side verification (`ipconfig /renew`). Reviewer added the missing step — a reminder that "correct" AI output can still be incomplete. |
| C009 | DNS server outage | Stale static DNS A record pointing to the wrong IP | Edited | The AI guessed a generic DNS failure mode instead of the specific evidence (`show hosts` mismatch). Reviewer corrected root cause and next_command. |
| C020 | DHCP pool exhaustion | VLAN30 pruned from the trunk allowed-list | Edited | AI pattern-matched "no IP address" to DHCP issues generally, without weighing the trunk evidence over the DHCP evidence. |
| C026 | Bad physical cable | Spanning-tree loop (no port blocking) | Rejected | The AI proposed a plausible but unsupported cause not backed by the actual evidence (multiple ports stuck forwarding). Reviewer rejected outright and supplied the correct diagnosis. |

## Patterns observed

- **Evidence under-weighting:** In 3 of 5 cases, the AI leaned on the most
  statistically common cause for a symptom category rather than the specific
  show-command evidence provided. This is the main risk this project's human
  review step is designed to catch.
- **"Correct but incomplete" is still a correction:** C007 shows that a
  right root cause doesn't guarantee a complete fix — reviewers still need to
  check `fix_steps` line by line.
- **Confidence labels tracked reality reasonably well:** cases the AI marked
  `medium`/`low` confidence (C003, C017, C029) were exactly where a second
  look was most warranted, which is the intended signal.

## Takeaway for the rule checker

Deterministic checks in `rule_checker.py` (interface state, VLAN/trunk
evidence, missing routes) catch several of these same categories
independently of the AI (see C020, C024, C027, C030 in the rule checker
report), giving reviewers a second, non-AI signal to weigh alongside the AI
diagnosis before accepting a fix.