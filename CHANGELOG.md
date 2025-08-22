# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-08-13
## [2.0.0] - 2025-08-22

### Added
- Optional import of FortiGate config files to build an in-app object catalog (addresses, groups, services, VIPs, vip groups) used at export-time for exact name mapping.
- FortiGate CLI export (policies only) including security profiles and logging settings.
- Unique policy-name enforcement (max 35 chars) with automatic suffixing and header summary.
- Guided Suggestions flow with one-by-one proposals and inline naming; resume to next group after any decision.
- Pre-export validation blocking unknown address/service names not present in loaded configs.
- Interface exclude list for CLI export (default: `_default`, `VLAN1`), configurable via `PM_INTERFACE_EXCLUDE`.

### Changed
- Address/service tokenization is now catalog-aware and greedy, preserving multi-word object names exactly as in configs.
- `_default.VLANX` expansion refined and SSL VPN interface mapping (`sslvpn_tun_intf` → `ssl.root`).
- Suggestions/merge unions honor dominance: `all`/`any` for addresses, `ALL` for services.

### Fixed
- Numerous GUI crashes (teaching tips timing, About page objectName, enum usages, missing methods).
- Deduplication no longer happens on import; user reviews and confirms in Dedupe page.
- Merges now correctly reduce Final Review count and persist after refresh.

### Added

-   Initialized project structure and documentation.
-   Created `PLAN.md` with a detailed development roadmap.
-   Created `TECH_SPECS.md` outlining the technology stack and architecture.
-   Created `README.md` with project overview.
-   Created `CHANGELOG.md` to track changes.
-   Initialized Git repository for version control.
 -   Added research substeps across all plan steps requiring Context7 and web references; will log sources in `docs/REFERENCES.md`.
-   Implemented CSV loader with header detection and FortiGate tag extraction; initial data models.
-   Implemented diff engine (identity grouping, Jaccard similarity) and merger utilities.
-   Added CLI tools: summary and interactive merge workflow (Phase 1 prototype).
-   GUI scaffold with PyQt6; merge dialog; diff dialog; compare selected; export merged CSV.
-   Batch merge CLI; session save/load; rotating file logging.
-   Tests for CSV loader; About dialog; version set to 0.1.0.
 -   Fluent UI shell (`policy_merger.gui.fluent_app`) with Import/Dedupe/Suggestions/Final Review/Export pages.
 -   Dedupe Review on five key fields with explicit confirmation and undo; audit logging.
 -   Suggestions view presenting single-field merge proposals with tabular rule list, union preview, and required name input.
 -   Final Review with inline editable table; Export to CSV.
 -   Theme toggle (light/dark) and accent controls; About page.

### Changed

-   Completed Phase 3.5/3.6 guided UX and transparency; plan/docs updated.

### Fixed

-   Various GUI crashes (icon constant, enums, export methods) and PyInstaller issues.
