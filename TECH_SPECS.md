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

### 4.1 Five-Field Identity and Similarity (Phase 3.6)
- Exact dedupe identity uses only: `srcaddr`, `dstaddr`, `srcintf`, `dstintf`, `service` (normalized, space-collapsed).
- Similarity suggestions consider only these five fields; per-field Jaccard on tokenized values for multi-value fields; union merges suggested.

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

-   Versioning: Semantic Versioning.
-   Packaging: PyInstaller one-file mode per platform with separate build profiles.
-   Dependency policy: pin versions in `requirements.txt`; periodically refresh via `pip-tools` (future).

## 13. Documentation and References Policy

-   Always consult up-to-date documentation using Context7 for key libraries (Pandas, PyQt6) and supplement with web examples when needed.
-   Record notable references at the bottom of source files or in `docs/REFERENCES.md` (future).
