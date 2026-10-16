# User and agent workflow

## User render path

```mermaid
flowchart TD
  U[User provides .txt or .md] --> CLI[uniscript-ink render]
  CLI --> P[Parse copy → IR]
  P --> S[Script coverage]
  S --> H[Apply one style profile]
  H --> L[Paginate on paper preset]
  L --> R[Level C glyph render]
  R --> Q[Quality report]
  Q --> E[JPG + manifest]
```

## Agent implementation path

```mermaid
flowchart TD
  A[Read AGENTS + handoff] --> B[Pick phase slice]
  B --> C[Code in .venv]
  C --> D[pytest]
  D --> E{Claims still true?}
  E -->|no| F[Fix docs or code]
  F --> D
  E -->|yes| G[Report + optional commit]
```

## Keeping handwriting identity stable

1. Load one profile per job (`--profile`).
2. Seed variation from `source_path + profile + title` so reruns are reproducible.
3. Do not swap fonts/profiles mid-document.
4. Language change only adapts shaping needs; ink, slant, spacing stay from the profile.
