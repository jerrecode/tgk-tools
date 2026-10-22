"""Conservative safety checks for added PR lines; not a human code review."""
import os
import re
import subprocess
import sys

base_name = os.environ.get("GITHUB_BASE_REF", "main")
if not re.fullmatch(r"[A-Za-z0-9._/-]+", base_name) or base_name.startswith("-"):
    print("::error::Invalid base branch name")
    raise SystemExit(2)

try:
    diff = subprocess.check_output(
        ["git", "diff", "--no-ext-diff", "--unified=0", f"origin/{base_name}...HEAD"],
        text=True,
        stderr=subprocess.PIPE,
    )
except subprocess.CalledProcessError as exc:
    print("::error::Unable to compute PR diff:", exc.stderr, file=sys.stderr)
    raise SystemExit(2)

rules = (
    ("remote-shell", re.compile(r"\\b(?:curl|wget)\\b[^\\n]*\\|\\s*(?:ba)?sh\\b"), "Review remote code before execution"),
    ("force-push", re.compile(r"\\bgit\\s+push\\b[^\\n]*--force\\b"), "Never force-push automatically"),
    ("delete-root", re.compile(r"\\brm\\s+-rf\\s+/(?:\\s|$)"), "Destructive filesystem-root deletion"),
)
findings = []
for line in diff.splitlines():
    if not line.startswith("+") or line.startswith("+++"):
        continue
    for name, pattern, description in rules:
        if pattern.search(line[1:]):
            findings.append(f"{name}: {description}: {line[1:160]}")

for finding in findings:
    print("::error::" + finding)
if findings:
    raise SystemExit(1)
print("Static PR safety patterns passed. Human review is still required.")
