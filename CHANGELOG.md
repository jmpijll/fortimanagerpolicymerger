# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-08-13

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
