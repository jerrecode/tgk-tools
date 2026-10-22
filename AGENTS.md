# TGK-Tools contributor/agent instructions

Shell UX first: commands should compose with pipes; return data only on stdout and errors on stderr; predictable exit codes (0 success, 1 cancellation, 2 usage/failure); robust `--help`. Use existing TGK native widgets rather than reimplementing them. Keep graphic primitives, Kivy import adapter and backend in `jerrecode/tgk`. Review PRs for shell injection, path traversal, clean exit on cancellation, proper Android lifecycle, memory limits, large directory handling, and regressions. No unattended merges without passing tests and an explicit review policy.

Further tools candidates: structured form builder, log tail, diff preview, SQLite browser, Markdown viewer, selection/clipboard shortcuts, color picker, lazy directory paging and search, performance overlay, and a JSON schema driven dialog DSL. Add tests and docs with each command.
