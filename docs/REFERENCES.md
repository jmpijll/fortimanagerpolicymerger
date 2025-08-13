# References

A living log of references used during development.

- Record step-by-step research notes here with links.

## Phase 1, Step 1.2 (CSV Parsing & Data Modeling)

- Pandas read_csv and to_csv options (headers, skiprows, encoding, quoting, dtype, engines, performance) — Context7: `/pandas-dev/pandas` (multiple sections)
  - Header/skiprows: user guide io snippets (header, skiprows) — ensures we can detect header row after preamble
  - Encoding and errors handling — `encoding`, `encoding_errors`
  - Engine selection — `engine='python'` for irregular CSVs
  - Preserving strings — `dtype=str`, `keep_default_na=False`
  - String dtype future inference — `pd.options.future.infer_string` notes (pandas 2.1+)

## FortiManager CSV format context

- CSV writing: use `DataFrame.to_csv(index=False, encoding='utf-8', quotechar='"')` as default; preserve input columns order where possible. Context7 pandas docs confirm parameters.

## Phase 1, Step 1.4-1.5 (CLI and Output)

- CLI UX patterns: simple text prompts for prototype; consider `questionary` for enhanced experience later. Keep prompts concise and always show `sourceFortiGateTag`.
- Deduplication strategy: identity signature built from key fields; batch merge CLI removes duplicates and writes merged CSV.

## Phase 1, Step 1.1 (Init & Setup)

- Python 3.10+ baseline; venv via `python -m venv`; pin core deps in `requirements.txt`.
- Packaging research noted for later (PyInstaller profiles per OS).
- Observed export sample headers include `policyid` and numerous UTM/profile fields; some preamble lines like `Firewall Policy` precede the header. The loader searches for the line containing `policyid` and uses that as header.

## Phase 2, Step 2.1 (UI/UX Design and Framework Setup)

- PyQt6 official docs (Context7): `/context7/www_riverbankcomputing_com-static-docs-pyqt6-module_index.html`
  - QMainWindow, QApplication, QAction, QFileDialog usage patterns
  - QAbstractTableModel and QTableView model/view patterns
- Qt 6 Model/View programming guide (Context7): `/context7/qt-6-docs`
  - Subclassing QAbstractTableModel: implement rowCount, columnCount, data, headerData; emit dataChanged/layoutChanged
  - Large table best practices
