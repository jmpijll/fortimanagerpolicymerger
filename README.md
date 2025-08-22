# FortiManager Policy Merger

A modern, cross‑platform desktop app to analyze, dedupe, merge, review and export FortiManager policy packages (CSV) with an opinionated, guided workflow. Built with Python + PyQt6 + QFluentWidgets.

## Highlights
- **Multi‑CSV import**: Load multiple FortiManager policy exports at once.
- **Five‑field identity**: Dedupe by `srcaddr`, `dstaddr`, `srcintf`, `dstintf`, `service` — review and confirm before applying.
- **Guided merge suggestions**: One‑by‑one proposals when only one of the five fields differs; inline naming required; accept/deny and proceed.
- **Catalog‑aware name handling (config import)**: Optionally load FortiGate config files; at export, we map addresses/services to exact existing names (multi‑word safe) and validate unknowns.
- **FortiGate CLI export (policies only)**: Generate `config firewall policy` with interfaces, addresses, services, schedule, action, NAT, security profiles and logging.
- **Safety and correctness**:
  - Catalog‑aware greedy parsing prevents split names like `Domain` + `Controllers` when the object is `Domain Controllers`.
  - Dominance rules: `all`/`any` for addresses, `ALL` for services.
  - Unique policy names enforced (max 35 chars) with numeric suffixes.
  - Interface excludes: `_default`, `VLAN1` filtered out by default in CLI.
- **Final Review**: Editable table prior to export.
- **Audit Log**: In‑app audit trail exportable to CSV/JSON.

> Current version: `2.0.0`

---

## Screens & Workflow
1. **Import**
   - Add multiple CSVs.
   - Optionally load FortiGate config files (`.conf`/`.txt`) to build an object catalog.
2. **Dedupe**
   - Review exact duplicates on the five key fields; actions: Keep First (default), Keep Both (rename), Promote.
3. **Suggestions**
   - One‑by‑one merge proposals for single‑field differences; provide a new rule name inline; Accept or Keep separate and auto‑advance.
4. **Final Review**
   - Edit the resulting list as needed.
5. **Export**
   - Export merged CSV.
   - Export FortiGate CLI (policies only). If configs were loaded, names are normalized/validated against the catalog.
6. **Audit**
   - Browse and export your session actions.

---

## Install & Run

### Requirements
- Python 3.10+
- macOS, Windows, or Linux

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### Run the GUI
```bash
PYTHONPATH=src .venv/bin/python -m policy_merger.gui.fluent_app
```

### Optional: Load FortiGate configs for catalog-aware export
- From the Import page, click “(Optional) Open FortiGate Configs” and select one or more configuration files.
- We parse:
  - `config firewall address`
  - `config firewall addrgrp`
  - `config firewall service custom`
  - `config firewall service group`
  - `config firewall vip`
  - `config firewall vipgrp`

> The catalog is only applied at export-time to map multi-word object names and to validate unknown names.

---

## Exporting FortiGate CLI (Policies Only)
- In Export, click “Export FortiGate CLI”.
- If a catalog was loaded, we will:
  - Greedily match multi-token names against known addresses/groups/services/VIPs/vipgrps.
  - Validate that every referenced name exists (unless dominated by `all`/`any` or `ALL`).
  - Block export if unknown names remain and show the first 50 offenders.
- Policy name uniqueness is enforced (max 35 characters). Any renamed items are summarized in commented lines at the top of the script.
- Interface excludes are applied to `srcintf`/`dstintf`:
  - Default excludes: `_default`, `VLAN1`.
  - You can add more via `PM_INTERFACE_EXCLUDE` (comma or space separated), e.g. `PM_INTERFACE_EXCLUDE="_mgmt, VLAN999"`.

Generated example snippet:
```text
config firewall policy
    edit 0
        set name "HQ-to-DC"
        set srcintf "port1"
        set dstintf "port2"
        set srcaddr "HQ-NET"
        set dstaddr "DC-NET"
        set service "HTTP" "HTTPS"
        set schedule "always"
        set action accept
        set utm-status enable
        set ips-sensor "Block-ALL-Medium-High-Critical"
        set logtraffic all
    next
end
```

---

## CLI Utilities
Quick checks from terminal:
```bash
# Summary across CSVs
PYTHONPATH=src .venv/bin/python -m policy_merger.cli <csv1> <csv2> ...

# Interactive merger
PYTHONPATH=src .venv/bin/python -m policy_merger.interactive_cli <csv1> <csv2> ... --out result.csv

# Batch dedupe (identical rules only)
PYTHONPATH=src .venv/bin/python -m policy_merger.batch_merge <csv1> <csv2> ... --out result.csv
```

---

## Troubleshooting
- “Unknown objects” in export dialog
  - Ensure you loaded the relevant FortiGate configs on Import so the catalog contains all object names.
  - Confirm multi‑word objects exist with the exact same spelling (quotes/spaces matter).
- GUI crashes on tips
  - TeachingTips are deferred; if you still see issues, re-run after page is shown.
- App quits with PyQt crashes on macOS exit
  - We use a safe exit workaround.

---

## Releases
- CI/CD: pushing a tag like `v2.0.0` triggers GitHub Actions to build Windows, macOS, and Linux binaries and attach them to a GitHub Release.
- Workflow: `.github/workflows/release.yml`.

---

## Roadmap & Docs
- Plan: `PLAN.md`
- Technical specs: `TECH_SPECS.md`
- Changelog: `CHANGELOG.md`
- References: `docs/REFERENCES.md`

---

## Contributing & Safety
- Never commit sample exports or generated `result.csv` — they are `.gitignore`d.
- Contributions are welcome via issues and PRs.
- License: MIT
