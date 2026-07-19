---
name: codex-review-cycle
description: Run OpenAI Codex CLI in review mode iteratively — fix issues, leave TODOs for disagreements, and re-run until clean or max 3 iterations.
allowed-tools:
  - Bash
---

# Codex Review Cycle

Run an iterative review-fix cycle (max 3 iterations) using best codex model.

## Important context

The codex reviewer is stateless — it has no memory between runs. Each iteration it reviews all uncommitted changes from scratch as if seeing them for the first time. This means it may raise the same issues again, change its mind on previous feedback, or contradict earlier suggestions. You must track state across iterations yourself.

## Bash execution rules

- **Never combine commands with `&&` or `;`.** Run each command as a separate Bash tool invocation so failures are visible and context stays clean.
- Each iteration's raw output is stored at `/tmp/codex-review-output-N.txt` by the helper script.

## Helper script

Use the bundled `codex-review-cycle-run.sh` script (in this skill's directory) for running codex and extracting clean output. Make sure it is executable before first use:
```bash
chmod +x codex-review-cycle/codex-review-cycle-run.sh
```

## State tracking

Maintain an internal log across iterations:
- **All issues ever raised** — indexed by file + location + issue description
- **Actions taken** — what you fixed, skipped, or commented on
- **Issue history** — track if an issue was raised, then not raised, then raised again (oscillation)

## For each iteration (1 through 3):

1. Run the helper script with the iteration number and any extra arguments. Use a 15-minute (900s) timeout on the Bash tool invocation:
   ```bash
   codex-review-cycle/codex-review-cycle-run.sh N $ARGUMENTS
   ```
   If the tool times out, log "⏰ Codex review timed out after 15 minutes" and **stop the cycle**.

2. **Print all issues found in this iteration before doing anything else.** List them clearly with file, location, and description. This gives full visibility before any changes are made.

3. Compare current issues against your internal log from previous iterations:
   - **New issue** — process normally (step 4).
   - **Recurring issue you already fixed** — the reviewer may have missed the fix or disagrees. Re-evaluate, but if you're confident your fix is correct, skip it.
   - **Oscillating issue** (reviewer flip-flops: raise → not raise → raise, or suggests contradictory fixes across iterations) — do NOT keep changing the code back and forth. Instead, add a comment documenting the different opinions:
     ```
     // NOTE(codex-review): Reviewer oscillated on this.
     // Iteration N: suggested X
     // Iteration M: suggested Y
     // Keeping current implementation.
     ```
     Mark the issue as resolved and **ignore it in all future iterations**.

4. For each new, non-oscillating issue:
   - **If you can confidently fix it** — apply the fix directly to the code.
   - **If you disagree or the fix is unclear** — leave a `// TODO(codex-review):` comment in the code explaining why the issue was skipped, and move on.

5. After addressing all issues, run all project checks (lint, typecheck, tests, build, etc.) to ensure nothing is broken. If any check fails, fix the failure before continuing.

6. Do not commit — leave changes as uncommitted so the next iteration picks them up.

7. **Stuck detection** — before proceeding to the next iteration, check:
   - Are the same issues repeating for 3+ iterations with no progress?
   - Are all remaining issues already marked as oscillating or skipped?
   - Is the set of issues not shrinking despite fixes being applied?
   If any of these are true, **exit the loop early** and report why.

8. Proceed to the next iteration.

## After the cycle ends

Provide a final summary:
- **Total iterations run**
- **Issues fixed** — list of fixes applied with file and brief description
- **Issues skipped (TODOs)** — list of disagreements left as TODO comments
- **Oscillating issues** — list of issues where the reviewer contradicted itself, with the different opinions noted
- **Final status** — whether the cycle exited clean, timed out, got stuck, or hit the 3-iteration limit
