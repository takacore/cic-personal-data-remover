# Security and privacy behavior

## Processing

This utility runs locally. It has no upload, telemetry, remote-analysis, or automatic-update feature. Installation of development dependencies is separate from application processing.

Input and output paths are restricted to local fixed disks. UNC paths, mapped network drives, device aliases, reparse points, and known cloud synchronization roots are rejected before input is read or output is written. This does not control unknown third-party backup/synchronization software, OS diagnostics, or the user's later sharing actions.

Input is parsed from an immutable in-memory snapshot. The snapshot's SHA-256 must match the analysis before processing. No original-PDF copy, OCR text, or work-image file is saved. Layouts that cannot be recognized are fully blacked out; page count and order are unrestricted.

Application-information and usage-record pages intentionally remove names only. Other visible values, including dates of birth, phone numbers, postal codes and receipt numbers, can remain. This is a selective masking policy, not complete de-identification. Credit, reference and summary pages retain the broader masking rules. Credit-guidance pages are not yet supported and remain fully blacked out when unrecognized; trailing pages are never unconditionally exempted.

Only a verified output reaches a collision-free, exclusively created temporary file. The file is replaced into the selected final location. Normal exceptions and Python interruptions clean up only the temporary file created by that call. Cleanup failure is reported. During processing, the application's close control waits for the worker to complete.

Forced OS termination or power loss during final writing can leave a verified-result temporary file. The onefile executable also extracts runtime components before Python starts, and those can remain after forced termination. This application does not promise secure physical deletion, empty pagefiles/crash dumps, or deletion of unrelated OS temporary files.

## Verification limits

The output is rebuilt from masked images. Checks cover page count, text layer, attachments, identifying metadata, links, annotations, widgets, XML metadata, table of contents, and executable document actions.

These are structural checks. The recognized templates use measured field geometry and do not prove that every visible identifier in every possible report is covered. Visually review all output pages before sharing. An unknown page is fully removed rather than passed through with its original content.

## Development and reporting

Regression fixtures contain synthetic values and are generated in temporary test directories. Do not commit actual disclosure reports, screenshots containing identifying details, OCR results, private keys, or access tokens. The repository audit script also checks every local Git object for workstation paths, credential patterns, and non-anonymous commit identities.

Report a masking error with synthetic data, layout coordinates, and steps to reproduce. Do not attach a real CIC report to an issue or pull request.
