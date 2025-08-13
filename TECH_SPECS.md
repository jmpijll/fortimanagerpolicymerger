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
