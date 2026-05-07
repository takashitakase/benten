# CLAUDE.md — benten

This file provides context and conventions for AI assistants (Claude, Copilot, etc.) working in this repository.

## Project Overview

**benten** is a project for collecting, organizing, and surfacing information about Japan's **2026 medical fee revision (2026年度診療報酬改定)**.

診療報酬改定 is the periodic revision of Japan's national medical fee schedule, administered by the Ministry of Health, Labour and Welfare (厚生労働省) based on recommendations from the Central Social Insurance Medical Council (中央社会保険医療協議会 / 中医協). The 2026 revision takes effect in the fiscal year starting April 2026 (令和8年4月).

Primary goals:
- Collect official revision documents, notices (通知), and data tables from authoritative sources
- Parse and structure fee schedule data (点数表) for downstream analysis or display
- Track changes between revision cycles

## Repository Structure

> The structure below is the planned layout. It will be updated as the project evolves.

```
benten/
├── src/           # Application source code
├── data/
│   ├── raw/       # Unmodified source files (PDFs, CSV, XML from 厚生労働省)
│   └── processed/ # Cleaned, structured data ready for use
├── tests/         # Test suite
└── docs/          # Supplementary documentation and references
```

## Development Setup

> Commands will be added here once the tech stack is decided.

```sh
# Example — replace with actual commands
# Install dependencies
# <command>

# Run tests
# <command>

# Start development server / run scripts
# <command>
```

## Key Conventions

### Language and Terminology

- **Preserve Japanese domain terms** in their original form. Do not translate or transliterate terms such as:
  - 診療報酬 (medical fee / medical reimbursement)
  - 改定 (revision)
  - 点数表 (fee schedule / point table)
  - 中医協 (Central Social Insurance Medical Council)
  - 告示・通知 (official notices)
  - DPC, 特定機能病院, 在宅医療, etc.
- Use Japanese when writing user-facing text that will be read by Japanese-speaking users.
- Use English for code identifiers, commit messages, and internal tooling unless the project explicitly adopts Japanese identifiers.

### Encoding

- All text files must be **UTF-8** (no BOM).
- Source data from 厚生労働省 may arrive in Shift-JIS or EUC-JP; convert to UTF-8 during ingestion and note the original encoding in a comment or metadata field.

### Dates

| Context | Format |
|---------|--------|
| Data fields / filenames | ISO 8601: `YYYY-MM-DD` |
| Display / documentation | Japanese fiscal year: `令和8年度` or `R8年度` |
| Revision effective date | `2026-04-01` (令和8年4月1日) |

### Data Attribution

Always record the source of every data file. Official sources for this project include:

- 厚生労働省 (Ministry of Health, Labour and Welfare) — mhlw.go.jp
- 中央社会保険医療協議会 (中医協) meeting materials
- 社会保険診療報酬支払基金 (SHIF)
- 国民健康保険中央会 (KOKUHO)

Store attribution metadata (source URL, retrieval date, original filename) alongside each raw file.

## AI Assistant Guidelines

1. **Do not fabricate regulatory values.** Medical fee points (点数), drug prices, and procedure codes are legally defined. If a value is unknown or ambiguous, flag it with a `TODO` comment and note the authoritative source to consult.

2. **Preserve Japanese terminology** as described above. When adding new identifiers for Japanese concepts, prefer romanized abbreviations only when there is an established industry convention (e.g., `DPC`, `DRG`); otherwise use descriptive English.

3. **Follow existing patterns** in file structure, naming, and data schemas before introducing new ones.

4. **Scope changes narrowly.** A data-ingestion fix should not silently refactor unrelated parsing logic.

5. **Cite sources in comments** when hard-coding values derived from official tables (e.g., point conversion rates, category codes).

## Testing

> Update this section once a test framework is in place.

- Unit tests live in `tests/`
- Run the full suite before committing: `<test command>`
- All new data-processing logic must have at least one test covering a representative real input

## Branch and Commit Strategy

- Default branch: `main`
- Feature work: short-lived branches off `main` — e.g., `feat/parse-r8-fee-schedule`
- PR-based workflow; squash-merge preferred
- Commit message format:
  ```
  <type>: <short English summary>

  Optional Japanese detail or context.
  ```
  Types: `feat`, `fix`, `data`, `docs`, `refactor`, `test`, `chore`

## Useful References

- 厚生労働省 令和6年度診療報酬改定 (prior cycle, useful for structure comparison)
- 中医協 総会 議事録・資料 — published at mhlw.go.jp
- 点数表 告示 (Official Gazette notices for the fee schedule)
