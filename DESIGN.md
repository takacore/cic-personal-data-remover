---
name: CIC Personal Data Remover
description: A secure, local-first inspection station for irreversibly removing personal data from verified CIC reports.
colors:
  shell-navy: "#0B1424"
  inspection-navy: "#111D30"
  control-navy: "#17263A"
  paper: "#F4F1E8"
  paper-panel: "#E9E6DC"
  paper-border: "#C9C5BA"
  ink: "#102033"
  light-ink: "#F7FAFC"
  shell-muted: "#AFC0D3"
  verified-teal: "#35D3BE"
  verified-teal-dark: "#0B7469"
  verified-teal-active: "#69E5D5"
  offline-surface: "#123A3A"
  offline-text: "#8EF2E5"
  safety-surface: "#0D2A30"
  safety-heading: "#A8F4E9"
  safety-copy: "#BED5D8"
  active-amber: "#F3B85B"
  refusal-red: "#A92626"
  error-bright: "#FF7A7A"
  deletion-black: "#000000"
  primary-disabled: "#33485A"
  primary-disabled-text: "#8192A4"
  secondary-border: "#36506A"
  secondary-active: "#223A53"
  progress-trough: "#24364A"
  paper-supporting: "#4B5A68"
  paper-metadata: "#5B6872"
  paper-status: "#53616D"
  paper-review: "#55616A"
  paper-footer: "#4B5751"
typography:
  display:
    fontFamily: "Noto Sans JP"
    fontSize: "26pt"
    fontWeight: 700
  app-title:
    fontFamily: "Noto Sans JP"
    fontSize: "22pt"
    fontWeight: 700
  section-title:
    fontFamily: "Noto Sans JP"
    fontSize: "12pt"
    fontWeight: 700
  button-primary:
    fontFamily: "Noto Sans JP"
    fontSize: "11pt"
    fontWeight: 700
  button-secondary:
    fontFamily: "Noto Sans JP"
    fontSize: "10pt"
    fontWeight: 700
  body:
    fontFamily: "Noto Sans JP"
    fontSize: "10pt"
    fontWeight: 400
  label:
    fontFamily: "Noto Sans JP"
    fontSize: "9pt"
    fontWeight: 400
  micro:
    fontFamily: "Noto Sans JP"
    fontSize: "8pt"
    fontWeight: 400
  step-number:
    fontFamily: "Bahnschrift"
    fontSize: "11pt"
    fontWeight: 400
rounded:
  square: "0px"
spacing:
  text-tight: "3px"
  text: "4px"
  control-gap: "10px"
  inset: "14px"
  column-gap: "18px"
  panel-x: "20px"
  section: "24px"
  content-y: "30px"
  content-x: "34px"
  window-x: "38px"
components:
  button-primary:
    backgroundColor: "{colors.verified-teal}"
    textColor: "{colors.ink}"
    typography: "{typography.button-primary}"
    rounded: "{rounded.square}"
    padding: "13px 20px"
  button-primary-active:
    backgroundColor: "{colors.verified-teal-active}"
    textColor: "{colors.ink}"
  button-primary-disabled:
    backgroundColor: "{colors.primary-disabled}"
    textColor: "{colors.primary-disabled-text}"
  button-secondary:
    backgroundColor: "{colors.control-navy}"
    textColor: "{colors.light-ink}"
    typography: "{typography.button-secondary}"
    rounded: "{rounded.square}"
    padding: "11px 16px"
  button-secondary-active:
    backgroundColor: "{colors.secondary-active}"
    textColor: "{colors.light-ink}"
  paper-panel:
    backgroundColor: "{colors.paper-panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "18px 20px"
  offline-badge:
    backgroundColor: "{colors.offline-surface}"
    textColor: "{colors.offline-text}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "7px 12px"
  step-badge:
    backgroundColor: "{colors.control-navy}"
    textColor: "{colors.shell-muted}"
    typography: "{typography.step-number}"
    rounded: "{rounded.square}"
    padding: "5px 0"
    width: "3 characters"
    height: "1 line"
  step-badge-active:
    backgroundColor: "{colors.active-amber}"
    textColor: "{colors.ink}"
  step-badge-complete:
    backgroundColor: "{colors.verified-teal}"
    textColor: "{colors.ink}"
  progress-indicator:
    backgroundColor: "{colors.verified-teal}"
    rounded: "{rounded.square}"
    height: "8px"
---

# Design System: CIC Personal Data Remover

## Overview

**Creative North Star: "The Secure Document Inspection Station"**

The interface treats a CIC report as sensitive material moving through a purpose-built inspection station. Deep navy chrome establishes a controlled, local environment; a broad paper-colored work surface keeps the document task legible; teal appears as an earned signal that a condition has been checked or an action is safe. Ruled panels, squared controls, and the black deletion band in the mark connect the utility directly to the physical language of forms and irreversible redaction.

The atmosphere is calm, procedural, and candid about risk. The three-step rail keeps the user on one linear path—inspect the PDF, delete personal information, verify safety—while status copy names disabled, working, verified, complete, and refusal states without relying on color. This is a native Windows utility, so density, keyboard-operable controls, system dialogs, and platform focus behavior remain native rather than being restyled into browser conventions.

**Key Characteristics:**

- Deep navy inspection shell surrounding one large paper work surface.
- A fixed three-step rail that makes destructive processing legible before it happens.
- Teal used sparingly for local, verified, complete, or safe-to-proceed states.
- Flat, square document geometry with thin ruled borders and no decorative elevation.
- Japanese-first typography with explicit, high-contrast operational copy.

## Colors

The palette separates the secure operating environment from the document surface, then uses small semantic signals to communicate safety, activity, and refusal.

### Primary

- **Verified Teal:** The primary action, completed step badges, progress fill, logo outline, and verified/local signals. Its brighter active state appears only while a primary control is engaged; its darker form carries successful status text on paper.

### Secondary

- **Inspection Navy:** The three-step rail and supporting control surfaces within the secure shell.
- **Control Navy:** Default secondary buttons and inactive step badges, keeping non-primary actions visually subordinate.

### Tertiary

- **Active Amber:** The current in-progress step. It communicates activity, not success.
- **Refusal Red:** Error and refusal status headings on paper. The brighter error token is reserved in the implementation palette for high-emphasis error treatment.
- **Deletion Black:** The literal redaction band in the brand mark and the destructive PDF output material; it is not an application-chrome color.

### Neutral

- **Shell Navy:** The window background and header field.
- **Paper:** The dominant task surface, chosen to evoke a physical report rather than a generic white application canvas.
- **Paper Panel:** File and review containers nested on the paper surface.
- **Paper Border:** One-pixel ruled boundaries around those containers.
- **Ink:** Primary text on paper and dark text on bright semantic fills.
- **Light Ink:** Primary text against navy controls and shell surfaces.
- **Shell Muted:** Supporting text in the dark rail and subtitle areas.
- **Paper Supporting Family:** Closely related gray-blue values distinguish explanatory copy, metadata, live status detail, review rows, and the compatibility footer without adding decorative color.
- **Disabled Navy:** A desaturated fill and text pairing that makes unavailable primary actions visibly inactive.

### Named Rules

**The Teal Must Be Earned Rule.** Use teal for verified, complete, local, or safe-to-proceed meaning; keep the save action disabled and desaturated until analysis succeeds.

**The Black Means Deletion Rule.** Pure black belongs to irreversible redaction and its identifying mark, never to decorative application panels.

## Typography

**Display Font:** Noto Sans JP
**Body Font:** Noto Sans JP
**Label/Number Font:** Noto Sans JP, with Bahnschrift only for step numerals

**Character:** A single Japanese sans-serif voice keeps security instructions plain and complete across glyphs. Weight and size create hierarchy; display styling, letter-spacing effects, and ornamental type are absent.

### Hierarchy

- **Display** (bold, 26pt): The single task heading on the paper surface.
- **App Title** (bold, 22pt): Product identification in the navy header.
- **Section Title** (bold, 12pt): The workflow-rail heading.
- **Control / Status Title** (bold, 11pt): Primary actions, filenames, and current status headings.
- **Body** (regular or bold, 10pt): Header description, step headings, supporting task instructions, and secondary actions.
- **Label** (regular or bold, 9pt): File metadata, status explanations, badges, and safety-note headings.
- **Micro** (regular, 8pt): Step notes, review detail, safety copy, and the compatibility footer.
- **Step Number** (regular Bahnschrift, 11pt): The only Latin display role, confined to the three numbered workflow badges.

### Named Rules

**The One Japanese Voice Rule.** Use Noto Sans JP for every user-facing sentence and control; reserve Bahnschrift for the compact 1–3 workflow numerals only.

## Layout

The native window opens at 1000 × 840 and does not shrink below 920 × 800. A 76 px header sits above the task body, both inset 38 px from the window edge. The body divides into a fixed 220 px workflow rail and an expanding paper surface separated by an 18 px gutter.

The paper surface uses 34 px horizontal and 30 px vertical insets. Content is stacked in workflow order: heading and instruction, file panel, live status and 8 px progress track, page-by-page review panel, then the bottom action row. Section separation is normally 24 px; panel interiors use 20 × 18 px or 14 px compact insets. The paper work surface expands with the window while the rail and its three stages remain stable.

**The One-Way Bench Rule.** Preserve the implemented top-to-bottom order and keep the primary save action at the lower edge of the paper surface; do not rearrange the workflow into tabs, floating panes, or a generic toolbar.

## Elevation & Depth

The system uses no shadows. Depth comes from tonal nesting: the navy window contains the darker inspection rail and the light paper work surface; within the paper, slightly darker panels are bounded by one-pixel rules. This keeps the utility closer to a document inspection bench than a stack of floating cards.

### Named Rules

**The Flat Evidence Rule.** Use tonal adjacency and one-pixel document rules for grouping; do not introduce drop shadows, glows, translucency, or floating-card elevation.

## Shapes

All visible surfaces and controls are rectangular with square corners. The geometry repeats the straight edges of CIC tables, ruled paper, progress bars, workflow badges, and black deletion bands. Borders are thin and structural: paper panels use a one-pixel rule, the secondary button uses a one-pixel navy rule, and the primary button is borderless.

**The Ruled Document Rule.** Keep corners square and boundaries orthogonal; rounded cards, pills, and ornamental silhouettes conflict with the implemented form language.

## Components

### Brand Mark

- **Character:** A 48 × 48 canvas containing a teal outlined document, two light rules, and a central black deletion band.
- **Role:** Connects product identity to document structure and irreversible redaction without adding an external image asset.

### Workflow Rail

- **Structure:** A fixed-width navy column with a heading, three stacked step rows, and a bottom-anchored original-file promise.
- **Default Step:** Control-navy badge with muted numeral; white heading and muted explanatory note.
- **Active Step:** Amber badge with dark ink while inspection or deletion is underway.
- **Complete Step:** Teal badge with dark checkmark after the stage completes.
- **Behavior:** Completed and active states are expressed by both badge color and badge content, so meaning is not color-only.

### Buttons

- **Shape:** Square, compact native controls with no corner radius.
- **Primary:** Verified teal with ink text, bold 11pt type, borderless treatment, and 20 × 13 px internal padding. It brightens in the active state.
- **Primary Disabled:** Desaturated navy fill and muted blue-gray text. The save action starts in this state and becomes available only after compatible-document analysis succeeds.
- **Secondary:** Control navy with light text, a one-pixel navy border, bold 10pt type, and 16 × 11 px internal padding. It shifts to the lighter active navy while engaged.
- **Focus:** Keep the native Windows/ttk focus and keyboard behavior; the implementation does not add a bespoke focus ring.

### File and Review Panels

- **Corner Style:** Square.
- **Background:** A warm gray paper inset against the lighter paper work surface.
- **Border:** One-pixel ruled border.
- **Internal Padding:** The file panel uses 20 × 18 px; the denser review panel uses 14 px horizontal and 10 px vertical insets.
- **Content:** The file panel holds filename, local path or page/count metadata, and the PDF chooser. The review panel holds a heading and a fixed-height scrollable page-by-page summary. Unrecognized pages are labelled for full-page blacking out before saving.

### Status and Progress

- **Status:** A bold title followed by explicit explanatory text. Ready and working titles use ink, verified and complete titles use dark teal, and refusal uses dark red.
- **Progress:** An 8 px square-ended teal indicator on a navy trough. Analysis may use indeterminate motion; deletion and verification report determinate progress.
- **State Copy:** Ready, scanning, deleting, structure-verified, complete, and refusal states each use distinct text. Name full-page deletion when any page is unrecognized. Completion always instructs visual review before sharing; it never claims all visible personal data was detected. Closing the window while processing is blocked until the worker finishes.

### Offline Badge and Safety Note

- **Offline Badge:** A compact rectangular teal-on-dark-teal label in the upper-right header; 12 × 7 px padding and bold 9pt type.
- **Safety Note:** A dark teal block anchored to the bottom of the workflow rail. Its bold heading promises the original PDF is unchanged; its smaller body explains that the output is image-only and contains no recoverable data under the black bands.

### Action Row

- **Structure:** Primary save and secondary reveal controls are left aligned with a 10 px gap; compatibility scope is right aligned in 8pt text.
- **State:** The reveal action stays disabled until an output exists. The scope note remains visible throughout the workflow.

## Do's and Don'ts

### Do:

- **Do** preserve the deep-navy shell, paper work surface, and teal verification hierarchy as one coherent inspection-station world.
- **Do** keep the three workflow stages visible and update each badge with number, checkmark, color, and explicit status copy.
- **Do** gate the teal save action behind successful compatibility analysis and keep unsupported-document refusal prominent in text.
- **Do** keep the original-file promise and page-by-page compatibility scope visible throughout the workflow; page count and order are unrestricted.
- **Do** use native Windows controls, dialogs, focus handling, and keyboard behavior.

### Don't:

- **Don't** turn the product into a generic PDF editor with toolbars, thumbnails, editing modes, or rearrangeable panels.
- **Don't** use teal as general decoration or show it on an action that is not yet safe to perform.
- **Don't** introduce rounded cards, pill controls, gradients, shadows, glass effects, or decorative illustration.
- **Don't** represent deletion as a translucent overlay; black means the underlying personal data is irreversibly removed.
- **Don't** communicate scanning, deletion, success, or refusal with color alone.
