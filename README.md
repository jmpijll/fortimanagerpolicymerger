# FortiManager Policy Merger

A modern, cross‑platform desktop app to analyze, compare, and merge FortiManager policy packages (CSV). Built with Python + PyQt6 + QFluentWidgets.

### Why you’ll love it ✨
- **Load many CSVs** at once and see everything in one place
- **Spot duplicates** instantly on five key fields: `srcaddr`, `dstaddr`, `srcintf`, `dstintf`, `service`
- **Get merge suggestions** where policies only differ in one of those five fields
- **Decide with confidence**: Keep A, Keep B, Keep Both (rename), or Merge fields (union)
- **Stay in control**: every dedupe/merge requires your explicit confirmation
- **Final Review**: edit the resulting table before export
- **Audit log**: track every action you took

### Screens and flow 🧭
1. **Import**: add multiple FortiManager CSV exports
2. **Dedupe**: review exact duplicates on the five fields; confirm per-group
3. **Suggestions**: one‑by‑one merge proposals for single‑field differences; name the result inline and accept/deny
4. **Final Review**: editable table for last tweaks
5. **Export**: write your consolidated CSV
6. **Audit**: browse and export your session actions

---

## Getting started 🚀

### Requirements
- Python 3.10+
- A virtual environment is recommended (`python -m venv .venv`)

### Install dependencies
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the GUI (Fluent UI)
```bash
PYTHONPATH=src .venv/bin/python -m policy_merger.gui.fluent_app
```
Guided flow: Import → Dedupe → Suggestions → Final Review → Export.

### CLI tools (for quick checks) 🧪
- Summary across CSVs:
```bash
PYTHONPATH=src .venv/bin/python -m policy_merger.cli <csv1> <csv2> ...
```
- Interactive merger:
```bash
PYTHONPATH=src .venv/bin/python -m policy_merger.interactive_cli <csv1> <csv2> ... --out result.csv
```
- Batch dedupe (identical rules only):
```bash
PYTHONPATH=src .venv/bin/python -m policy_merger.batch_merge <csv1> <csv2> ... --out result.csv
```

---

## Releases 📦
- Pushing a tag like `v1.0.0` triggers GitHub Actions to build Windows, macOS, and Linux packages and attach them to a GitHub Release.
- Workflow file: `.github/workflows/release.yml`.

Current version: `1.0.0`

---

## Docs 📚
- Plan and status: `PLAN.md`
- Technical specs: `TECH_SPECS.md`
- Changes: `CHANGELOG.md`
- Research references: `docs/REFERENCES.md`

---

## Notes on data safety 🔒
- `exports/` and `result.csv` are ignored and must never be committed.
- If you fork, keep those paths in your `.gitignore`.

---

## Contributing 🤝
We welcome feedback and ideas to make the UX even smoother. Open issues or PRs and let’s improve it together!

License: MIT
