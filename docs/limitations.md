# Limitations (Phase 1)

| Area | Current behaviour |
|------|-------------------|
| Inputs | `.txt` and `.md` only |
| Handwriting | Level C glyph fallback with controlled jitter/slant |
| Math | Treated as plain text runs; structured math planned |
| Figures / tables | Not sketched yet; Markdown tables become plain text lines |
| RTL shaping | Detected and warned; full HarfBuzz/FriBidi path planned |
| Scan effects | Subtle optional; clean mode default |
| UI | CLI only |
| Models | None required for Phase 1 |

If a feature is unsupported, the pipeline records a warning and continues when safe. It does not invent content or hide failures with visual noise.
