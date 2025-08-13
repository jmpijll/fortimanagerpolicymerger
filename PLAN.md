# FortiManager Policy Merger - Project Plan

This document outlines the phased development plan for the FortiManager Policy Merger application.

## Phase 1: Core Logic and Foundation (CLI First)

This phase focuses on building the essential backend functionality. We will start with a command-line interface (CLI) to test and validate the core logic before building the GUI.

*   **Step 1.1: Project Initialization & Setup**
    *   [x] Initialize Git repository.
    *   [x] Create initial documentation files (`PLAN.md`, `TECH_SPECS.md`, `README.md`, `CHANGELOG.md`).
    *   [ ] Create `.gitignore` for Python projects.
    *   [ ] Create project structure (e.g., `src` directory).
    *   [ ] Setup Python virtual environment and `requirements.txt`.
    *   [ ] Make the first commit.

*   **Step 1.2: CSV Parsing and Data Modeling**
    *   [ ] Analyze the structure of the sample CSV files from the `exports` folder.
    *   [ ] Develop a robust CSV parsing module (using Pandas) to read policy data.
    *   [ ] Define Python classes/data structures to represent firewall policies, address objects, services, etc.
    *   [ ] Extract the source FortiGate name from the filename for each imported policy set.

*   **Step 1.3: Policy Comparison (Diffing) Engine**
    *   [ ] Implement a function to compare two policy rules and identify differences.
    *   [ ] Develop logic to find "similar" rules based on predefined criteria (e.g., same source/destination interfaces, similar services).
    *   [ ] The engine should be able to pinpoint specific field-level differences (e.g., different destination IPs).

*   **Step 1.4: Interactive Merging Logic (CLI)**
    *   [ ] Create a CLI-based interaction loop to present conflicts/merge-opportunities to the user.
    *   [ ] Implement the core merge actions:
        *   **Keep:** Choose one rule and discard the other.
        *   **Keep Both (Rename):** Keep both rules, appending a suffix to one to resolve name conflicts.
        *   **Merge Fields:** Combine values from specific fields (e.g., destination IPs) into a single rule.
    *   [ ] Ensure the source FortiGate name is always displayed in user prompts for context.

*   **Step 1.5: Output Generation**
    *   [ ] Implement functionality to write the final, merged policy set to a new CSV file.
    *   [ ] Ensure the output format is clean and consistent.

## Phase 2: Graphical User Interface (GUI)

This phase focuses on building a user-friendly graphical interface on top of the core logic.

*   **Step 2.1: UI/UX Design and Framework Setup**
    *   [ ] Finalize the choice of GUI framework (e.g., PyQt6).
    *   [ ] Design the main application window layout.
    *   [ ] Mock up the key UI components (file loader, policy display, diff view, merge dialogs).

*   **Step 2.2: GUI Implementation**
    *   [ ] Develop the file loading interface to allow users to add/remove CSV files.
    *   [ ] Create a tabular or tree-based view to display loaded policies.
    *   [ ] Build a sophisticated "diff view" that clearly highlights differences between two policies side-by-side.
    *   [ ] Implement interactive dialogs for making merge decisions, replacing the CLI prompts.

*   **Step 2.3: Integration and Packaging**
    *   [ ] Connect the GUI to the backend core logic from Phase 1.
    *   [ ] Package the application into a standalone executable for Windows, macOS, and Linux using PyInstaller.

## Phase 3: Advanced Features and Refinements

This phase adds features that enhance the user experience and application robustness.

*   **Step 3.1: Session Management**
    *   [ ] Allow users to save their merging session (loaded files, decisions made) and resume later.

*   **Step 3.2: Testing and Quality Assurance**
    *   [ ] Write unit tests for the core parsing and merging logic.
    *   [ ] Conduct manual testing of the GUI across different platforms.

*   **Step 3.3: Logging**
    *   [ ] Implement logging to record user actions and application events for easier debugging.

## Phase 4: FortiGate CLI Script Generation

This is a major feature for a future release, converting the merged policy into executable FortiGate CLI.

*   **Step 4.1: CLI Conversion Engine**
    *   [ ] Design the mapping from the internal data model to FortiGate CLI syntax.
    *   [ ] Implement converters for:
        *   Address Objects & Groups
        *   Service Objects & Groups
        *   VIPs and IP Pools
        *   Firewall Policies
    *   [ ] Add a feature to export the generated script to a `.txt` or `.scr` file.
