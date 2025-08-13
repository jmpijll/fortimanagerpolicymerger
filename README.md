# FortiManager Policy Merger

A multi-platform desktop application to analyze, compare, and merge firewall policy packages exported from FortiManager.

## About The Project

This tool is designed to simplify the process of consolidating firewall policies from multiple FortiGates. When managing a large estate of firewalls, it's common to have duplicated or slightly varied policies across different devices. This tool helps security administrators by:

*   **Loading** multiple policy CSV exports.
*   **Intelligently finding** similar or conflicting rules.
*   **Providing a clear UI** to decide whether to **keep**, **discard**, or **merge** policies.
*   **Exporting** a single, clean, and consolidated policy package.

The end goal is to produce a unified policy set that can be re-imported or used as a base for creating deployment scripts, reducing complexity and improving security posture.

## Features

*   **Multi-File Import:** Load and process multiple CSV files at once.
*   **Conflict Detection:** Automatically identifies rules that are identical or similar.
*   **Interactive Merging:** A user-friendly GUI to resolve conflicts with options to:
    *   Keep one rule and discard another.
    *   Keep both by renaming one.
    *   Merge fields from multiple rules into one.
*   **Context-Aware:** Always shows the original FortiGate source for each policy.
*   **Merged Export:** Outputs a single, clean CSV file of the consolidated policies.
*   **(Future) CLI Script Generation:** Convert the final policy set into FortiGate CLI commands.

## Getting Started

*(This section will be updated as the project progresses)*

### Prerequisites

*   Python 3.10+

### Installation

1.  Clone the repo
    ```sh
    git clone [repo-url]
    ```
2.  Install dependencies
    ```sh
    pip install -r requirements.txt
    ```

## Roadmap and Docs

-   Development plan: see `PLAN.md`.
-   Technical details and architecture: see `TECH_SPECS.md`.
-   Changes over time: see `CHANGELOG.md`.
-   Sample input CSVs are in `exports/`.

## Usage

### CLI (temporary)

Run a summary across CSVs:
```bash
PYTHONPATH=src python -m policy_merger.cli exports/RG-ASA-LZ-FW-20250813-065650.csv
```

Run the interactive merger and write output:
```bash
PYTHONPATH=src python -m policy_merger.interactive_cli \
  exports/RG-ASA-LZ-FW-20250813-065650.csv exports/RG-NLD-CAP-FW-01-20250813-062755.csv \
  --out merged/merged_policies.csv
```

## License

Distributed under the MIT License. See `LICENSE` for more information.
