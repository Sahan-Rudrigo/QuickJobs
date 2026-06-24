---
name: frontend-design-modern
description: >
  Advanced minimalist frontend design skill. Use when building UI that must feel
  refined, airy, and architecturally precise — light theme, large generous
  viewboxes, modern editorial spacing, and a single memorable signature element.
  Supersedes the base frontend-design skill when the brief calls for clean,
  high-end, contemporary aesthetics.
triggers:
  - minimalist UI
  - light theme design
  - modern dashboard
  - clean frontend
  - airy layout
  - large view
  - spacious UI
  - advanced modern design
---

# Frontend Design — Modern Minimalist (Light Theme Edition)

You are the lead designer at a studio that specialises in software that feels
**inevitable**: every pixel is where it is for a reason, every element earns its
place, and the whole reads as effortless restraint rather than decoration.

---

## 0 · Before you design: anchor the brief

State in one sentence:
1. **Subject** — what is this product / page for?
2. **Audience** — who uses it and what do they need to feel?
3. **Single job** — the one thing this screen must accomplish.

Never skip this step. It determines every colour, weight, and spacing choice
that follows.

---

## 1 · Design Philosophy

### Minimalism as conviction, not absence

Minimalism is not removing things until nothing is left — it is keeping only what
is irreplaceable and then making each kept element do twice the work. Ask of every
component: *"If I removed this, would the user lose something they need?"*

### Light theme as a quality signal

The light palette in this system is **warm-neutral, not stark white**. Pure white
reads clinical; our whites are slightly warm (`#FAFAF8` to `#F5F4F1`). Contrast
lives in weight and spacing rather than darkness.

### Large viewboxes as breathing room

Every major content region (cards, panels, data blocks, hero areas) has generous
interior padding. The default internal padding of a "comfortable" component is
`48px` (desktop) → `32px` (tablet) → `24px` (mobile). This is your floor, not
your ceiling.

---

## 2 · Token System

### 2a · Colour — warm-light palette

| Token                  | Value     | Role                                              |
|------------------------|-----------|---------------------------------------------------|
| `--bg-base`            | `#FAFAF8` | Page background                                   |
| `--bg-surface`         | `#F2F1EE` | Card / panel background                           |
| `--bg-elevated`        | `#FFFFFF` | Modal, popover, tooltip background                |
| `--bg-sunken`          | `#EBEBEA` | Input field, code block background                |
| `--border-subtle`      | `#E4E3E0` | Dividers, card outlines (1 px)                    |
| `--border-default`     | `#CECCC8` | Interactive element borders                       |
| `--text-primary`       | `#1A1917` | Headlines, labels, body                           |
| `--text-secondary`     | `#6B6963` | Subtext, placeholders, captions                   |
| `--text-tertiary`      | `#A09C96` | Disabled, hint text                               |
| `--accent-1`           | `#2563EB` | Primary CTA, links, focus ring (blue-600)         |
| `--accent-1-soft`      | `#EFF4FF` | Accent tint for backgrounds                       |
| `--accent-2`           | `#16A34A` | Success / confirm (green-600)                     |
| `--accent-warn`        | `#D97706` | Warning (amber-600)                               |
| `--accent-danger`      | `#DC2626` | Error, destructive (red-600)                      |
| `--shadow-sm`          | `0 1px 3px rgba(0,0,0,0.06)` | Card resting shadow              |
| `--shadow-md`          | `0 4px 16px rgba(0,0,0,0.08)` | Elevated shadow                 |
| `--shadow-lg`          | `0 12px 40px rgba(0,0,0,0.10)` | Modal / drawer shadow          |

> **Rule**: No more than two accent hues on a single screen. One dominant
> (`--accent-1`), one contextual (success / warn / danger).

### 2b · Typography

| Role         | Face                       | Weight | Size (desktop) | Leading |
|--------------|----------------------------|--------|----------------|---------|
| Display      | `'Inter'` or `'Geist'`     | 700    | 48–72 px       | 1.05    |
| Heading 1    | Same                       | 600    | 32 px          | 1.15    |
| Heading 2    | Same                       | 600    | 24 px          | 1.2     |
| Heading 3    | Same                       | 500    | 18 px          | 1.3     |
| Body         | `'Inter'` or `'Geist'`     | 400    | 15–16 px       | 1.6     |
| Caption      | Same                       | 400    | 12–13 px       | 1.5     |
| Code / Mono  | `'JetBrains Mono'`         | 400    | 13 px          | 1.7     |
| Label / UI   | Same as Body               | 500    | 13–14 px       | 1.4     |

**Letter-spacing rule**:
- Display / H1: `−0.02em` (tight)
- H2–H3: `−0.01em`
- Body: `0`
- Label / Caption: `+0.01em`
- All-caps label: `+0.06em`

### 2c · Spacing scale (8-point grid)

```
4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 80 · 96 · 128
```

Use these values only. Never ad-hoc values like 7 px or 22 px. The grid is the
system; the system is the trust.

### 2d · Border radius

| Context                   | Value         |
|---------------------------|---------------|
| Card, panel, modal        | `16px`        |
| Button (default)          | `10px`        |
| Button (pill/CTA)         | `9999px`      |
| Input, select             | `10px`        |
| Badge, chip               | `6px`         |
| Tooltip                   | `8px`         |
| Avatar                    | `50%`         |
| Full-bleed section        | `0`           |

### 2e · Motion

| Token              | Value              | Use                               |
|--------------------|--------------------|-----------------------------------|
| `--dur-fast`       | `120ms`            | Hover colour, icon swap           |
| `--dur-default`    | `200ms`            | Most transitions                  |
| `--dur-enter`      | `280ms`            | Modal / popover enter             |
| `--dur-page`       | `400ms`            | Page-level transitions            |
| `--ease-default`   | `cubic-bezier(.4,0,.2,1)` | General motion           |
| `--ease-spring`    | `cubic-bezier(.34,1.56,.64,1)` | Bounce-in for delightful moments |
| `--ease-out`       | `cubic-bezier(0,0,.2,1)` | Exit transitions             |

**Use motion only when it communicates state change or guides attention. Ambient
animation is permitted but must be opt-out via `prefers-reduced-motion`.**

---

## 3 · Layout Architecture

### Page skeleton (desktop-first)

```
┌──────────────────────────────────────────────────────┐
│  NAV   logo ················ links · avatar          │  64 px tall
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              HERO / PAGE HEADER              │   │  min 240 px
│  │  Eyebrow · H1 · Subhead · CTA               │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐     │
│  │  CARD / A  │  │  CARD / B  │  │  CARD / C  │     │  min 180 px each
│  └────────────┘  └────────────┘  └────────────┘     │
│                                                      │
│  ┌──────────────────────────┐  ┌───────────────┐    │
│  │  MAIN CONTENT            │  │  SIDEBAR      │    │
│  │  (prose, table, chart)   │  │  (filters,    │    │
│  │                          │  │   metadata)   │    │
│  └──────────────────────────┘  └───────────────┘    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

- Max content width: **1280 px**, centred with `auto` side margins
- Side padding (container): `80px` desktop · `40px` tablet · `24px` mobile
- Section vertical rhythm: `96px` gap between major sections on desktop

### Card / panel rules

A card's interior breathing room defines its premium feel:

```css
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 40px 48px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--dur-default) var(--ease-default);
}
.card:hover { box-shadow: var(--shadow-md); }
```

---

## 4 · Component Patterns

### Buttons

```css
.btn-primary {
  background: var(--accent-1);
  color: #fff;
  padding: 12px 24px;
  border-radius: 10px;
  font-weight: 500;
  font-size: 14px;
  letter-spacing: 0.01em;
  transition: opacity var(--dur-fast), transform var(--dur-fast);
}
.btn-primary:hover  { opacity: 0.88; transform: translateY(-1px); }
.btn-primary:active { opacity: 1;    transform: translateY(0); }
```

### Input fields

```css
.input {
  width: 100%;
  padding: 12px 16px;
  background: var(--bg-sunken);
  border: 1px solid transparent;
  border-radius: 10px;
  font-size: 15px;
  color: var(--text-primary);
  transition: border-color var(--dur-fast);
}
.input:focus {
  outline: none;
  border-color: var(--accent-1);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-1) 15%, transparent);
}
```

---

## 5 · What to avoid

| Anti-pattern                        | Why                                                     |
|-------------------------------------|---------------------------------------------------------|
| Pure `#FFFFFF` background           | Clinical; use warm near-white instead                   |
| Gradients on body text              | Kills legibility and feels dated                        |
| More than 2 font families           | Visual noise                                            |
| Box shadows on every card           | Cheapens the surface                                    |
| Border-radius inconsistency         | Breaks the system                                       |
| Animation on every interaction      | Reserve for meaningful state changes                    |
| Nested cards (card inside card)     | Use `--bg-sunken` inset blocks instead                  |

---

## 6 · Quick reference card

```
PALETTE     base #FAFAF8 · surface #F2F1EE · elevated #FFF
            border-subtle #E4E3E0 · text #1A1917 · accent #2563EB
SPACING     4·8·12·16·24·32·48·64·80·96·128 (8-pt grid)
CARD PAD    48px desktop · 32px tablet · 24px mobile (floor, not ceiling)
RADIUS      card 16 · btn 10 · pill 9999 · input 10 · badge 6
SHADOW      sm 0 1 3 .06 · md 0 4 16 .08 · lg 0 12 40 .10
TYPE        Inter 700 display · 600 h1 · 500 h2-ui · 400 body
MOTION      fast 120ms · default 200ms · enter 280ms
MAX-WIDTH   1280px container · 680px prose
```
