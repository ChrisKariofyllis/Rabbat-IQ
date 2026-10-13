---
name: Rabbat-IQ
description: Self-hosted local grocery offer scout and supermarket leaflet matcher
colors:
  forest-green: "#1e6a43"
  forest-green-press: "#154e31"
  forest-green-light: "#e5f3eb"
  market-gold: "#f3c969"
  market-gold-deep: "#c4922a"
  market-gold-light: "#fbf3dc"
  warm-paper: "#f3efe6"
  paper-border: "#e7e1d4"
  sheet-surface: "#fffcf7"
  sheet-surface-warm: "#fbf6ea"
  ink-black: "#1c1915"
  ink-muted: "#5e584e"
  alert-red: "#8c2f2f"
  alert-red-bg: "#f8e8e4"
typography:
  display:
    fontFamily: '"Liberation Serif", "Times New Roman", Times, serif'
    fontSize: "clamp(1.7rem, 2.4vw, 2rem)"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'
    fontSize: "1.375rem"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'
    fontSize: "1.125rem"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  label:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  price:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
rounded:
  xs: "8px"
  sm: "10px"
  md: "12px"
  lg: "14px"
  pill: "999px"
spacing:
  space-1: "4px"
  space-2: "8px"
  space-3: "12px"
  space-4: "16px"
  space-5: "24px"
  space-6: "32px"
  space-7: "48px"
  pad: "20px"
  control: "44px"
components:
  button-primary:
    backgroundColor: "{colors.forest-green}"
    textColor: "{colors.sheet-surface}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.forest-green-press}"
  button-secondary:
    backgroundColor: "{colors.sheet-surface}"
    textColor: "{colors.forest-green}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    height: "44px"
  chip:
    backgroundColor: "{colors.market-gold}"
    textColor: "{colors.ink-black}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "44px"
  card-panel:
    backgroundColor: "{colors.sheet-surface}"
    rounded: "{rounded.lg}"
    padding: "20px"
  input-field:
    backgroundColor: "{colors.sheet-surface}"
    textColor: "{colors.ink-black}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
    height: "44px"
---

# Design System: Rabbat-IQ

## Overview

**Creative North Star: "The Grocer's Ledger"**

Rabbat-IQ bridges tactile newsprint flyers and the quiet utility of a household pantry ledger. Built for households scanning supermarket deals in Germany and Austria, the visual language avoids generic SaaS minimalism and loud e-commerce gimmicks. It treats grocery flyers with editorial respect: physical paper tones, deliberate serif mastheads, authoritative ink-black typography, and purposeful retail accents inspired by supermarket price tags.

The system lives on a physical paper canvas (`#f3efe6`) upon which crisp, warm white paper sheets (`#fffcf7`) rest with subtle dual-tier shadows. Key retail affordances—vibrant grocery gold (`#f3c969`) for discount pills and active tabs, deep forest green (`#1e6a43`) for primary actions and confirmed savings—bring warmth and instant scanability without visual clutter.

**Key Characteristics:**
- **Paper & Ink Materiality:** Warm natural paper backgrounds with rich charcoal ink text, avoiding sterile pure-white and harsh blue-black contrasts.
- **Editorial Typography Pairing:** Classic serif page titles evoking physical newspaper mastheads paired with highly legible system sans-serif for high-density offer comparisons.
- **Strict Touch Target Geometry:** A guaranteed 44px minimum touch target height across buttons, navigation items, chips, and inputs for effortless mobile handling in the kitchen or aisle.
- **Tabular Precision:** Consistent tabular figures (`font-variant-numeric: tabular-nums`) across prices, percentages, distances, and quantities.

## Colors

The palette draws from traditional Central European grocery store leaflets: newsprint paper, grocer's ledger ink, forest green stamps, and supermarket flyer gold highlights.

### Primary
- **Forest Green** (`#1e6a43`): Primary call-to-action button, brand icon base, and emphasis text. Represents confirmed matches and frugality.
- **Deep Forest Press** (`#154e31`): Hover and active states for primary actions; persistent link color in light mode.
- **Mint Wash** (`#e5f3eb`): Background tint for success banners, positive status alerts, and local flyer scope tags.

### Secondary
- **Market Gold** (`#f3c969`): High-energy accent reserved for discount callout chips, active navigation pills, and text selection.
- **Amber Gold** (`#c4922a`): High-visibility focus rings and geolocation marker dot ("You" pin on the map).
- **Butter Wash** (`#fbf3dc`): Soft highlight container background and broader regional leaflet tags.

### Neutral
- **Warm Paper** (`#f3efe6`): Light-mode page canvas; reminiscent of tactile uncoated newsprint.
- **Deep Paper Border** (`#e7e1d4`): Hairline boundary for cards, input strokes, and table dividers.
- **Sheet Surface** (`#fffcf7`): Elevated card and panel container background, creating gentle separation from the paper base.
- **Warm Sheet Hover** (`#fbf6ea`): Subtle interactive hover tint on ledger cells and flyer cards.
- **Charcoal Ink** (`#1c1915`): High-contrast primary reading text and headings; grounded deep warm black.
- **Muted Ink** (`#5e584e`): Secondary metadata, timestamps, store addresses, footnotes, and hints.

### Status & Feedback
- **Alert Red** (`#8c2f2f`): Error banner text and destructive button labels.
- **Alert Wash** (`#f8e8e4`): Error banner background and destructive button hover wash.

### Named Rules
**The Rarity of Gold Rule.** Market gold (`#f3c969`) is reserved strictly for active states, saved deals, and discount callouts. It must never coat background containers or neutral cards. In dark mode the hierarchy inverts by design: gold becomes the primary action, link, and emphasis color against the `#1c1915` canvas, and still never coats containers or neutral cards.

**The Paper Invariant Rule.** The page background must never be pure white (`#ffffff`). The warm paper base (`#f3efe6` in light, `#1c1915` in dark) anchors the physical identity across all surfaces. When `prefers-contrast: more` is active in dark mode, the canvas deepens to `#12100e` to maximize edge contrast.

## Typography

**Display Font:** Liberation Serif (with "Times New Roman", Times, serif fallback)
**Body Font:** System UI (-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif)
**Label/Mono Font:** System UI with `font-variant-numeric: tabular-nums`

**Character:** A deliberate pairing between an authoritative mid-century editorial serif heading and a neutral, crystal-clear system sans body designed for speed and tabular grocery scanning.

### Hierarchy
- **Display / H1** (Bold 700, `clamp(1.7rem, 2.4vw, 2rem)`, line-height 1.15, letter-spacing -0.02em): Section and page titles (Overview, Stores, Flyers). Set exclusively in Liberation Serif with `text-wrap: balance`.
- **Headline / H2** (Semi-bold 650, `1.375rem`, line-height 1.25, letter-spacing -0.02em): Card group headings, section headers, and modal titles.
- **Title / H3** (Semi-bold 650, `1.125rem`, line-height 1.3, letter-spacing -0.02em): Deal titles, card titles, and ledger metric values.
- **Body** (Regular 400, `1.0625rem` / 17px, line-height 1.45): Primary copy, instructions, and list item text. Max measure constrained to `68ch`.
- **Subhead / Control** (Semi-bold 600, `0.9375rem` / 15px, line-height 1.3): Navigation links, button labels, and filter controls.
- **Price Callout** (Bold 700, `1.5rem`, line-height 1.2, letter-spacing -0.02em): Large offer discount price display with tabular numerals.
- **Footnote / Caption** (Regular 400 / Bold 700, `0.8125rem`–`0.75rem`, line-height 1.3): Store addresses, timestamps, scope tags, and metric labels.

### Named Rules
**The Tabular Pricing Rule.** Any price, discount percentage, countdown date, or geographic distance must declare `font-variant-numeric: tabular-nums` to ensure stable vertical alignment in lists and ledgers.

**The Balanced Title Rule.** Display H1 and Headline H2 elements must include `text-wrap: balance` to prevent orphan words on narrow displays.

## Layout

The layout uses a centered single-column frame with a sticky top bar, built for responsive browsing on phones, tablets, and desktop workstations.

- **Maximum Width Container:** The `.frame` wrapper is restricted to `min(960px, calc(100% - 32px))` centered with `margin-inline: auto`.
- **Vertical Rhythm:** Page sections stack vertically with `var(--space-6)` (32px) gaps; internal card padding defaults to `var(--pad)` (20px).
- **Grid Models:**
  - **Ledger Bar:** 4-column equal grid on desktop, shifting to a 2x2 grid below 800px.
  - **Cards Grid:** Auto-fill CSS grid with `minmax(240px, 1fr)` and 14px gaps.
  - **Map Layout:** Split layout (`1.1fr` list, `0.9fr` sticky map) on desktop, stacking vertically with a 300px fixed map below 800px.
- **Safe Area Insets:** Layout respects `env(safe-area-inset-top)` on sticky navbar and `env(safe-area-inset-bottom)` on footer.

### Named Rules
**The 44px Touch Floor Rule.** Every clickable control, button, input field, and navigation tab must satisfy `min-height: 44px` (`--control: 44px`) to guarantee accessibility across handheld devices.

## Elevation & Depth

Rabbat-IQ utilizes warm tactile sheet layering rather than heavy skeuomorphism or floaty ambient blurs.

- **Tonal Layering:** The depth hierarchy starts with the base page background (`--color-bg: #f3efe6`), followed by surface sheets (`--color-surface: #fffcf7`), and interactive fills (`--color-fill: #fbf3dc`).
- **Hairline Definition:** All elevated containers have an explicit boundary via `1px solid var(--color-border)` (`#e7e1d4`).
- **Sheet Shadow:** Standard panels, cards, and maps use a dual-tier shadow:
  `box-shadow: 0 1px 2px var(--color-shadow), 0 8px 20px color-mix(in srgb, var(--color-ink) 8%, transparent);`
  This grounds the sheet firmly on the paper surface without dramatic blur radius.

### Named Rules
**The Sheet-on-Paper Rule.** Elevation never stacks more than two levels deep: the paper canvas, and the interactive sheet container. Cards do not sit inside floating cards.

## Shapes

- **Surface Containers (`14px` radius):** Cards (`.deal`, `.flyer`), status rows, ledger bars, and form panels use `--radius: 14px` for friendly, organic sheet corners.
- **Interactive Buttons (`12px` radius):** Primary, secondary, and scan buttons use `border-radius: 12px`.
- **Form Controls & Photos (`10px` radius):** Text inputs, dropdowns, textareas, deal photos, and map containers use `border-radius: 10px`.
- **Pill Geometry (`999px` radius):** Badges, notification counters, discount tags (`.off`), scope pills (`.scope`), and keyword chips (`.chip`) use full capsule radii.

### Named Rules
**The Capsule Semantics Rule.** Full rounded pill geometry (`999px`) is reserved exclusively for metadata tags, status pills, filter chips, and count indicators. Buttons and cards never use full capsules.

## Components

### Buttons
- **Primary:** Background `#1e6a43`, text `#fffcf7`, radius `12px`, padding `8px 16px`, min-height `44px`, font-weight `700`.
- **Hover / Press:** Transitions to `#154e31`.
- **Secondary:** Background `#fffcf7`, border `1px solid #e7e1d4`, text `#1e6a43`.
- **Destructive:** Background transparent, border transparent, text `#8c2f2f`; on hover receives `#f8e8e4` wash.
- **Disabled:** Background `#fbf3dc`, text `#5e584e`, cursor `not-allowed`.

### Chips & Badges
- **Interest Chip:** Background `#f3c969`, text `#1c1915`, radius `999px`, padding `0 14px`, min-height `44px`, font-weight `650`.
- **Discount Badge (`.off`):** Background `#f3c969`, text `#1c1915`, radius `999px`, padding `2px 8px`, font-weight `700`.
- **Scope Pill (`.scope-local`):** Background `#e5f3eb`, text `#154e31`, uppercase `font-size: 0.75rem`, letter-spacing `0.04em`.
- **Scope Pill (`.scope-broader`):** Background `#fbf3dc`, text `#1c1915`, uppercase.

### Cards & Containers
- **Deal Card (`.deal`):** Background `#fffcf7`, border `1px solid #e7e1d4`, radius `14px`, padding `14px`, dual-tier shadow. Features deal photo (`aspect-ratio: 4 / 3`), price callout (`1.5rem` bold tabular), and strike-through original price.
- **Flyer Card (`.flyer`):** Background `#fffcf7`, border `1px solid #e7e1d4`, radius `14px`, overflow hidden; image cover (`aspect-ratio: 3 / 4`); hover receives `#fbf6ea` warm wash.
- **Panel (`.panel`):** Background `#fffcf7`, border `1px solid #e7e1d4`, radius `14px`, padding `20px`.

### Inputs & Fields
- **Text & Select (`input`, `select`, `textarea`):** Background `#fffcf7`, border `1px solid #e7e1d4`, radius `10px`, min-height `44px`, padding `10px 12px`, caret-color `#1e6a43`.
- **Focus State:** Outline `3px solid #c4922a`, outline-offset `2px`.
- **Custom Checkbox (`.check`):** Aligns a `1.25rem` checkbox with label text, accent-color `#1e6a43`.

### Navigation
- **Navbar (`.navbar`):** Sticky top bar with semi-translucent backdrop (`color-mix(in srgb, #fffcf7 88%, transparent)`), 1px bottom border.
- **Site Nav Links:** Pill links (`border-radius: 999px`), min-height `44px`, hover background `#fbf3dc`. Active link takes `#f3c969` gold background with dark text.
- **Count Indicator (`.count`):** Pill counter badge inside nav link (`font-variant-numeric: tabular-nums`).

### Signature Components
- **The Metric Ledger (`.ledger`):** 4-column connected panel displaying total matches, stores, flyers, and scan cadence. Outer border with internal `1px` column dividers. Each cell highlights a bold tabular metric in forest green.
- **The Store Pin (`.store-pin`, `.you-pin`):** Map marker pin dot (`18px`) dynamically tinted with chain brand colors (`--chain-edeka: #1565c0`, `--chain-lidl: #f5c400`, etc.), with a 2px white halo and lift shadow. On hover (`.is-hot`), scales to 1.22x with a color-matched pulse ring.

## Do's and Don'ts

### Do:
- **Do** wrap every pricing display, discount tag, and distance indicator in `font-variant-numeric: tabular-nums`.
- **Do** ensure all clickable elements have at least `44px` height and explicit `:focus-visible` ring outlines.
- **Do** use `Liberation Serif` exclusively for H1 page titles; keep body, lists, and data tables in system sans-serif.
- **Do** preserve the warm paper canvas (`#f3efe6` light / `#1c1915` dark) for all new screens.
- **Do** apply `text-wrap: balance` to major headlines to prevent dangling words on mobile.

### Don't:
- **Don't** use pure `#ffffff` as a background color on any surface; use `#fffcf7` for elevated sheets and `#f3efe6` for base pages.
- **Don't** use Market Gold (`#f3c969`) as a large container background; reserve it for badges, chips, and active highlights.
- **Don't** remove the hairline `1px solid #e7e1d4` border from elevated cards and panels.
- **Don't** invent external font CDNs or webfont links; fonts must render from local assets or standard system UI fallbacks.
- **Don't** shrink touch targets below `44px` on mobile or desktop viewports.
