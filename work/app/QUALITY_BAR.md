# Quality Bar: Secure Document Inspection Station

## Thesis

The app should feel like a dedicated inspection station for one sensitive document workflow, never a generic PDF editor. The user can understand and finish the job without learning PDF terminology.

## Palette

- Deep navy shell: `#0B1424`
- Inspection panel: `#111D30`
- Paper work surface: `#F4F1E8`
- Verified/local accent: `#35D3BE`
- Irreversible deletion: pure black

## Materials and Type

Paper, ruled document geometry, and black deletion bands provide the material language. Japanese UI copy uses Noto Sans JP for complete glyph coverage and a clear native hierarchy.

## First Viewport

A three-step inspection rail occupies the left. The large paper surface on the right holds file selection, compatibility status, page-by-page detection review, progress, and the final save action in that order.

## Controls and States

The primary action is teal only when safe to proceed. Disabled, scanning, deleting, verifying, success, and refusal states are all explicit in text. The original-file promise remains visible throughout.

## Honest Risk

Detect supported table geometry per page without fixing page count or order. Unrecognized or structurally uncertain pages are fully blacked out rather than retained unchanged. Explain full-page deletion before saving and in the completion message. PDF structure verification is not proof that every visible identifying value was found; always ask users to review all output pages before sharing.
