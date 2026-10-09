# Product

<!-- impeccable:product-schema 1 -->

## Platform

Windows desktop (native)

## Stack

Confirmed: distributed as a single Windows desktop application (`.exe`). Implementation details are delegated to the build, with no separate runtime installation required for the user.

## Users

Inferred from the brief: a person handling their own or an authorized subject's CIC disclosure report who needs to share or retain the credit-information portion without exposing identifying details.

## Product Purpose

Mask the designated identifying-value regions of supported CIC layouts and save a separate image-only PDF. Unknown layouts are fully blacked out. Success verifies PDF structure and applied regions; users must visually review all pages before sharing. Compatibility is not a guarantee that every historical report or visible identifying value has been detected.

## Positioning

The tool is purpose-built around the field structure of CIC disclosure reports and uses destructive redaction plus verification, rather than placing cosmetic rectangles over recoverable PDF content.

## Operating Context

The user selects a CIC PDF on Windows, reviews detected personal-information categories and a page-by-page count, then saves a sanitized copy. Processing stays on the local computer. The original PDF remains unchanged.

## Capabilities and Constraints

- Confirmed: mask designated personal-information regions in supported layouts and rebuild output without original PDF objects.
- Confirmed: deliver as a single Windows application.
- Confirmed: no application upload or telemetry. Local-path gates reject UNC, mapped network drives, known synchronization roots, and reparse points; third-party backup/synchronization behavior remains outside the application.
- Confirmed: layouts are detected page by page, so reports with extra pages, omitted pages, or a different page order can still be exported.
- Confirmed: each unrecognized page is fully blacked out and counted explicitly, so it cannot silently pass through unchanged.
- Preserve credit contract, payment, inquiry, and registration information unless it is itself an identifying value.
- Personal-information categories include names, dates of birth, sex, addresses, postal codes, personal and workplace phone numbers, workplace names, public identification numbers, spouse information, receipt/reference numbers, and free-text identity comments.
- Application-information and usage-record pages are an explicit exception: mask names only and preserve other visible information, including identifying values. Explain this selective policy before saving; do not claim complete anonymization.
- Credit guidance is not yet supported. Keep unknown pages fully blacked out regardless of their position, until a validated guidance layout is implemented.

## Evidence on Hand

- A seven-page sample report was reviewed locally during development. It is not stored in this repository. Synthetic fixtures cover the corresponding table geometries without containing actual identifying data.
- No claims about compatibility with every historical CIC layout may be fabricated; compatibility is verified against the supplied sample and guarded by document/layout checks.

## Product Principles

- Removal must be irreversible, not merely visual.
- Never modify or overwrite the original report.
- Be tolerant of report structure differences while making every unrecognized page conspicuous for manual checking.
- Keep rendering and verification in memory. Commit verified output through an exclusively created temporary file. Retain no input copies or work images. Never claim cleanup is guaranteed after power loss or forced termination.
- Make the result auditable with detection counts and a verification outcome that reveal no sensitive values.

## Accessibility & Inclusion

Use keyboard-accessible native Windows controls, clear Japanese labels, high-contrast status states, and progress/error text that does not depend on color alone.
