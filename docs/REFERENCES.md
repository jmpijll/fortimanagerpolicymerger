# References

A living log of references used during development.

- Record step-by-step research notes here with links.

## Phase 1, Step 1.2 (CSV Parsing & Data Modeling)

- Pandas read_csv and to_csv options (headers, skiprows, encoding, quoting, dtype, engines, performance) — Context7: `/pandas-dev/pandas` (multiple sections)
  - Header/skiprows: user guide io snippets (header, skiprows) — ensures we can detect header row after preamble
  - Encoding and errors handling — `encoding`, `encoding_errors`
  - Engine selection — `engine='python'` for irregular CSVs
  - Preserving strings — `dtype=str`, `keep_default_na=False`

## FortiManager CSV format context

- Observed export sample headers include `policyid` and numerous UTM/profile fields; some preamble lines like `Firewall Policy` precede the header. The loader searches for the line containing `policyid` and uses that as header.
