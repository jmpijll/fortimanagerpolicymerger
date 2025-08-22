# Technical Specifications

This document details the technical requirements, architecture, and technology stack for the FortiManager Policy Merger application.

## 1. Core Requirements

-   **Functional:**
    -   Load multiple FortiManager policy export CSV files.
    -   Identify and display differences ("diffs") between similar policy rules.
    -   Provide an interactive interface for users to resolve conflicts.
    -   Merge policies based on user decisions (keep, keep-both-renamed, merge-fields).
    -   Extract and display the source FortiGate name for context.
    -   Export the final merged policy set to a single CSV file.
-   **Non-Functional:**
    -   **Platform:** Must run on Windows, macOS, and Linux.
    -   **Performance:** Must efficiently handle large policy sets (thousands of rules).
    -   **UI/UX:** Must have a clean, modern, and intuitive graphical user interface.
    -   **Maintainability:** Code must be clean, well-documented, and easy to maintain.

## 2. Architecture

The application will be built with a decoupled architecture:

-   **Backend/Core Logic (Python):** A standalone module responsible for all business logic:
    -   CSV Parsing and I/O
    -   Data Modeling
    -   Diffing Engine
    -   Merging Engine
    -   This ensures the logic can be tested independently and can be driven by either a CLI or a GUI.
-   **Frontend/GUI (Python + PyQt6):** A graphical interface that consumes the backend module.
    -   It will be responsible for all user interaction and data visualization.
    -   It will not contain any business logic.

## 3. Technology Stack

-   **Programming Language:** **Python 3.10+**
    -   *Reasoning:* Excellent cross-platform support, extensive libraries for data manipulation and GUI development, and a large developer community.

-   **Core Libraries:**
    -   **Pandas:** For high-performance CSV parsing and data manipulation. It is the industry standard for handling tabular data in Python.
    -   **PyQt6:** For the graphical user interface.
        -   *Reasoning:* It provides modern, native-looking widgets, is highly customizable, and has strong commercial support and a vibrant community. It is a mature and reliable choice for building professional desktop applications. We will use Context7 to ensure we are using up-to-date practices for implementation.

-   **Development & Distribution:**
    -   **Git:** For version control.
    -   **v_env:** For managing project dependencies.
    *   **PyInstaller:** For packaging the application into a single, distributable executable for multiple operating systems.
    *   **GitHub/GitLab/etc:** Suggested for remote repository hosting and CI/CD, for now we will be working locally.

## 4. Data Model

-   The core data model will be represented by Python classes. For example:
    -   `FirewallPolicy`
    -   `AddressObject`
    -   `ServiceObject`
    -   `PolicyRule`
-   Each policy rule will have attributes for all possible fields (name, source interface, destination address, service, action, etc.).
-   A `PolicySet` class will manage a collection of rules loaded from a single CSV, including metadata like the source FortiGate name.

### 4.1 Five-Field Identity and Single-Field Merge Suggestions (Phase 3.6)
- Exact dedupe identity uses only: `srcaddr`, `dstaddr`, `srcintf`, `dstintf`, `service` (normalized, space-collapsed).
- Merge suggestions are presented when four of the five fields match and one differs (name/policyid ignored). The differing field is unioned across the group; the other four remain unchanged.

## 5. CSV Format Assumptions and Parsing

-   Input files are FortiManager CSV exports. Observed characteristics:
    -   May include a title/preamble line (e.g., `Firewall Policy`) before the header.
    -   Header row contains `policyid` and other policy fields.
    -   CSV values are quoted; fields can contain spaces and multi-value lists expressed as space-separated tokens inside a single quoted field.
-   Parsing rules:
    -   Skip all lines before the first row that contains the `policyid` column.
    -   Treat the entire cell string as authoritative; do not naïvely split by spaces when the semantics are ambiguous (e.g., `Domain Services`).
    -   For multi-value fields, Phase 1 will compare at the raw string level. Phase 2+ will introduce robust tokenization aided by object dictionaries (addresses, services, groups) to correctly parse names that include spaces.
    -   Preserve column order and unknown columns for round-trip fidelity.

## 5.1 Session Persistence (Phase 3.6)
- Session JSON includes: `version`, `columns`, `rules`, `audit_log`.
- On load: restore table model and audit log (Audit page) for transparency.

## 6. Source FortiGate Extraction

-   Each imported file is tagged with a `sourceFortiGateTag` derived from the filename.
-   Pattern: base filename without extension, with trailing timestamp removed.
    -   Regex: `^(?P<device>.+?)-\d{8}-\d{6}$` → use `device` as `sourceFortiGateTag`.
    -   If no timestamp suffix is found, use the full base filename.
-   This tag is displayed in all user prompts and included in merge audit logs.

## 7. Rule Identity, Similarity, and Merge Strategy

-   Canonicalization (Phase 1):
    -   Trim whitespace, normalize repeated spaces to one inside fields, lowercase for boolean-like fields (`enable`/`disable`).
    -   Key fields for identity: `srcintf`, `dstintf`, `srcaddr`, `dstaddr`, `service`, `schedule`, `action`, `nat`.
    -   A rule “identity signature” is the tuple of these normalized fields.
-   Similarity detection:
    -   Two rules are “similar” if they share all identity fields except one or two fields from: `srcaddr`, `dstaddr`, `service`.
    -   Field-level similarity score (Phase 2): Jaccard similarity on token sets for multi-value fields; exact match for scalar fields. Weighted aggregate score with configurable weights.
-   Merge actions:
    -   Keep A or Keep B.
    -   Keep Both (Rename): append suffix `-from-<sourceFortiGateTag>` or `(<n>)` to `name` to disambiguate.
    -   Merge Fields: union the differing multi-value fields while preserving alphabetical order (Phase 2) or original order (Phase 3 with dictionaries).
-   Conflict audit:
    -   All decisions are recorded with timestamp, user choice, and `sourceFortiGateTag` for traceability.

## 8. CLI Interaction Flow (Phase 1)

-   Load files → derive `sourceFortiGateTag` per file.
-   Present detected identical/similar groups one-by-one:
    -   Show `policyid`, `name`, and key fields side-by-side; include `sourceFortiGateTag`.
    -   Prompt: Keep A, Keep B, Keep Both (Rename), Merge Fields, Skip.
-   Save interim state to a session file (`.yaml`/`.json`) to allow resume.

## 9. GUI Interaction Flow (Phase 2)

-   Views:
    -   File Loader with per-file `sourceFortiGateTag` badges.
    -   Policies table with filters and grouping by similarity sets.
    -   Diff panel with side-by-side comparison and per-field merge controls.
-   Undo/Redo stack for decisions; progress indicator across similarity sets.

## 10. Error Handling, Logging, and Validation

-   Input validation: detect malformed CSV, missing headers, or unsupported encodings; provide actionable messages.
-   Logging: structured logs (`jsonl`) with user actions and errors; rotating files in a `logs/` directory.
-   Audit: in-app audit log records dedupe/merge actions and supports export (CSV/JSON) with filters and search.
-   Safety checks: prevent duplicate `policyid` in the final export; auto-reassign or prompt to resolve.

## 11. Performance Targets

-   Handle 10k+ policies across files on commodity hardware.
-   Use Pandas for bulk operations; avoid O(n^2) comparisons by hashing identity signatures and bucketing by stable keys.

## 12. Packaging and Versioning

-   Versioning: Semantic Versioning (current: 1.0.0).
-   Packaging: PyInstaller one-file mode per platform with separate build profiles.
-   Dependency policy: pin versions in `requirements.txt`; periodically refresh via `pip-tools` (future).

## 13. Documentation and References Policy

-   Always consult up-to-date documentation using Context7 for key libraries (Pandas, PyQt6) and supplement with web examples when needed.
-   Record notable references at the bottom of source files or in `docs/REFERENCES.md` (future).

## 14. FortiGate CLI Generation (Phase 4)

This section specifies how the merged policy set is converted into FortiGate CLI scripts. The goal is to generate readable, idempotent scripts that can be applied safely to a unit (or via FortiManager) and re-run without unintended changes.

### 14.1 Scope
- Address objects (IPv4)
- Address groups
- Custom services (TCP/UDP)
- Service groups
- VIPs (static NAT and port-forward)
- IP pools (overload / one-to-one)
- Firewall policies

### 14.2 Ordering rules (creation before use)
1) `config firewall address`
2) `config firewall addrgrp`
3) `config firewall service custom`
4) `config firewall service group`
5) `config firewall vip`
6) `config firewall ippool`
7) `config firewall policy`

Objects are created/updated before any policy references them. Groups are emitted after their member objects. Policies are emitted last.

### 14.3 Idempotency strategy
- Emit full desired state for each object using `edit "<name>"` followed by `set ...` statements, then `next`. Re-running yields the same result.
- For groups, prefer `set member "a" "b" ...` with the complete, sorted final list to avoid accidental duplicates. Where safe incremental updates are required, use `append member` / `unselect member`.
- When creating new policies, use `edit 0` to allocate the next available ID, plus `set name "<policy-name>"` to make re-runs deterministic by name.
- Avoid destructive deletes in generated scripts. Provide a separate “cleanup” mode in the future.

### 14.4 Name normalization
- Preserve original names where possible. If normalization is required, apply:
  - Trim; collapse internal whitespace; keep ASCII; replace unsupported quotes with `-`.
  - Enclose names in quotes in CLI to support spaces.
- Ensure uniqueness within each object table; append `-1`, `-2` if needed.

### 14.5 Field mapping from model → CLI
- Address (IPv4 host/network):
  - CLI: `config firewall address` → `edit "<name>"` → `set subnet <ip> <mask>` → optional `set comment "..."` → `next`
- Address Group:
  - CLI: `config firewall addrgrp` → `edit "<name>"` → `set member "<addr1>" "<addr2>" ...` → `next`
- Service (custom):
  - CLI: `config firewall service custom` → `edit "<name>"`
    - If TCP ports present: `set tcp-portrange 80-80 443-443` (ranges space-separated)
    - If UDP ports present: `set udp-portrange 500-500 4500-4500`
    - Optional: `set comment "..."`
    - `next`
- Service Group:
  - CLI: `config firewall service group` → `edit "<name>"` → `set member "HTTP" "HTTPS" ...` → `next`
- VIP (static NAT / port-forward):
  - CLI: `config firewall vip` → `edit "<name>"`
    - `set extip <public-ip>`
    - `set mappedip "<private-ip>"`
    - Optional: `set extintf "<wan>"`
    - For DNAT: `set portforward enable` + `set extport <p>` + `set mappedport <p>`
    - `next`
- IP Pool:
  - CLI: `config firewall ippool` → `edit "<name>"` → `set startip <ip>` `set endip <ip>` → optional `set type overload` → `next`
- Policy:
  - CLI: `config firewall policy` → `edit 0`
    - `set name "<name>"`
    - `set srcintf "<if1>"` `set dstintf "<if2>"`
    - `set srcaddr "<addr-or-group>" ...`
    - `set dstaddr "<addr-or-group>" ...`
    - `set service "<svc-or-group>" ...`
    - `set schedule "always"` (or mapped value)
    - `set action accept|deny`
    - Optional: `set nat enable` (and `set ippool enable` `set poolname "<pool>"`)
    - Optional: `set comments "<from-merger>"`
    - `next`

### 14.6 Generation rules
- Emit only objects referenced by at least one final policy unless the user opts into “emit all discovered objects”.
- Sort emission deterministically (by name) to produce stable diffs.
- When an aggregated field contains multiple values (e.g., `service`), map to service groups automatically when names exceed a threshold (configurable), or emit as a space-separated list when appropriate.
- Schedule defaults to `always` unless present in input.

### 14.7 Validation & safety checks
- Detect and prevent invalid references (e.g., group member not emitted).
- Enforce interface consistency for address groups where the platform requires it.
- Validate port ranges and IP formats prior to emission; fail early with a clear message.

### 14.8 Script layout and ergonomics
- Start of script: comment banner with version, timestamp, and file sources.
- Add `config system console\n    set output standard\nend` as a preamble tip (commented) for long outputs.
- Group sections with comment headers, e.g., `# Addresses`, `# Services`.

### 14.9 Example snippets
- Address
```
config firewall address
    edit "HQ-NET"
        set subnet 10.10.0.0 255.255.0.0
        set comment "Generated by Policy Merger 1.0.0"
    next
end
```
- Policy
```
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
        set nat enable
    next
end
```

### 14.10 References (representative)
- Fortinet FortiOS CLI Reference (addresses, services, VIPs, ippool, policy): see Fortinet documentation portal: [docs.fortinet.com](https://docs.fortinet.com/)
- Tips on `append`/`unselect member` for groups: [yurisk.info](https://yurisk.info/2022/02/21/fortigate-cli-tips-to-avoid-costly-mistakes-save-time-make-you-more-effective/)
- Administration and best practices articles: [community.fortinet.com](https://community.fortinet.com/)
