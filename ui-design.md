# ui-design.md — Guru Line (design brief + master prompt for a design/build platform)

Use this file with Lovable, Antigravity, v0, Stitch, or Claude Code. Paste **Section 1** as the prompt, and keep the rest as reference.

---

## 0. Research notes: what the two reference sites teach us

**Bolna Buildathon page** (the event you're pitching to):
- Dark hero with soft arc/dot patterns, huge headline, short sub-line ("Bring any idea. Give it a voice.").
- Numbered steps `01 → 06` for the timeline, big and scannable.
- Sponsor logo strip (Plivo, Exotel, Sarvam, Cartesia, Deepgram, Kalpa Labs).
- One clear call to action repeated ("Apply now"). Very little copy per block.

**Oklo** (design quality bar):
- Editorial restraint: huge type, generous whitespace, almost no decoration.
- One strong sentence per section: "One company. Three reinforcing business lines." Then three equal cards.
- Large cinematic imagery, quiet nav, news list with dates, simple footer.
- Confidence comes from clarity and space, not from effects.

**Takeaways for Guru Line**
1. Dark, calm, premium. One accent color. Big type. Lots of space.
2. Numbered flows (`01 Call → 02 Detect → 03 Remember → 04 Recall`).
3. One sentence per section; three equal cards when listing.
4. The **live graph** is the cinematic hero (it replaces Oklo's photography).
5. Do not copy either site's logos, images or wording. Take the *principles*.
6. Sponsor-aware footer: "Built with Bolna · Sarvam" (only technologies you actually used).

---

## 1. MASTER PROMPT (paste this)

```
Design and build a modern, premium web app called "Guru Line" for a phone-call AI tutor.

STYLE: dark, editorial, calm, cinematic. Inspired by minimal deep-tech sites: huge confident
typography, generous whitespace, one warm accent colour, thin 1px borders, subtle grain,
soft radial glows. No clutter, no stock illustrations, no gradients-on-everything.

STACK: Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui, framer-motion,
react-force-graph-2d, Recharts, Supabase Realtime. Fully responsive. Dark theme default.

PAGES:
1. Landing (/): hero "A tutor on a normal phone call that remembers every mistake."
   Sub: "No app. No smartphone. Just a call." Primary CTA "Hear a demo call". Numbered flow
   01-04. Three equal cards (Calls / Memory / Proof). Live mini-graph that gently animates.
   Footer with "Built with Bolna and Sarvam".
2. Live Session Console (/live): THE DEMO SCREEN. 3 columns on desktop:
   left = live transcript with misconception chips; centre = large live knowledge graph;
   right = confidence vs accuracy chart + mastery bars + "next review" list.
   Top bar: student name (first name only), topic, call timer, pulsing "LIVE" dot, waveform.
   A "Demo Mode" toggle makes everything larger for a projector.
3. Student Memory (/students/[id]): explorable graph, timeline of sessions, misconception
   strength over time, "What Guru remembers" list with source session and a delete button.
4. Teacher Dashboard (/teacher): class heat-map of misconceptions, students needing support
   (no rankings), 3-line summaries, suggested class action.
5. Parent Update (/parent/[id]): large Hindi/English toggle, three warm sentences, a simple
   progress ribbon. Very simple, mobile first.
6. Proof (/proof): eval report - "Correct misconception identified in X / 30 synthetic students",
   accuracy chart, hints-to-solve chart, and real pilot before/after cards. Label synthetic vs real.
7. Privacy Center (/privacy): consent status, data sources, export and delete buttons.

BEHAVIOUR: /live subscribes to Supabase Realtime table live_events. When an attempt event
arrives, the matching graph node pulses, the edge colour changes, a chip appears in the
transcript, and the chart animates. Provide a simulator button that replays a scripted session
so the UI can be demoed without a real call.

Follow the design system below exactly. Provide empty, loading and error states for every view.
```

---

## 2. Design system

### 2.1 Colour tokens
```css
:root {
  --bg:        #07080A;   /* page */
  --surface:   #0D0F13;   /* cards */
  --surface-2: #14171D;   /* raised */
  --line:      #232832;   /* 1px borders */
  --text:      #F2F3F5;   /* primary text */
  --muted:     #8B93A1;   /* secondary text */
  --accent:    #FF9A3D;   /* warm saffron: CTAs, live dot, active node */
  --accent-2:  #FFD08A;   /* accent soft */
  /* mastery scale (colour-blind aware: also use icons/labels) */
  --m-low:     #E5484D;   /* < 0.4  */
  --m-mid:     #F5A524;   /* 0.4-0.7 */
  --m-high:    #3DD68C;   /* > 0.7  */
  --misc:      #B794F6;   /* misconception nodes */
}
```
Light theme (optional): `--bg:#F6F5F2; --surface:#FFFFFF; --text:#0B0C0E; --line:#E4E1DA` with the same accent.

### 2.2 Typography
- Headlines: **Instrument Serif** or **Fraunces** (editorial feel), weights 400, tight tracking.
- UI/body: **Inter Tight** (or Inter).
- Data/numbers: **JetBrains Mono**.
- Hindi: **Noto Sans Devanagari** (must render cleanly everywhere).

| Style | Size / line | Use |
|---|---|---|
| Display | clamp(44px, 7vw, 96px) / 1.0 | Landing hero |
| H1 | 48 / 1.05 | Page titles |
| H2 | 32 / 1.15 | Sections |
| Body | 16 / 1.6 | Text |
| Small | 13 / 1.5 | Labels, captions |
| Mono | 13 / 1.4 | Numbers, IDs, timers |

### 2.3 Spacing, radius, elevation
- 8px base grid. Section padding: 120px desktop, 72px mobile.
- Radius: 16px cards, 999px chips, 10px inputs.
- No heavy shadows. Use 1px `--line` borders plus a faint glow: `0 0 80px rgba(255,154,61,.08)`.
- Subtle film grain overlay at 3% opacity. Radial glow behind hero graph.

### 2.4 Motion (framer-motion)
- Page and section reveal: fade + 12px rise, 400ms, `cubic-bezier(.2,.7,.2,1)`.
- Graph node pulse on update: scale 1 → 1.35 → 1, 600ms, ring in `--accent`.
- Edge colour tween 500ms when mastery crosses a threshold.
- Numbers count up (mastery %, confidence).
- Respect `prefers-reduced-motion`: disable pulses and parallax.

### 2.5 Iconography
Lucide, 1.5px stroke. Used sparingly.

---

## 3. Layout specs

### 3.1 Landing
1. **Nav:** logo left, links (Live, Proof, Privacy), CTA right. Transparent, blurs on scroll.
2. **Hero:** Display headline, one-line sub, two buttons ("Hear a demo call", "See it live"), a faint animated graph behind the text (radial mask). Phone number chip under the buttons.
3. **Numbered flow** `01 Call · 02 Detect · 03 Remember · 04 Recall` as a horizontal row of large numerals with one line each.
4. **Three equal cards:** Calls (no app needed), Memory (graph that learns), Proof (measured, not claimed). Each card: icon, 1 sentence, a small live visual.
5. **Big quote section:** "It doesn't just mark answers wrong. It finds why."
6. **Footer:** minimal, "Built with Bolna and Sarvam", privacy link, team name.

### 3.2 Live Session Console (the winning screen)
```
┌─────────────────────────────────────────────────────────────────────────┐
│ ● LIVE  Rahul · Linear equations · 03:42    ▂▃▅▇▅▃▂ waveform            │
├───────────────┬───────────────────────────────────┬─────────────────────┤
│ TRANSCRIPT    │         KNOWLEDGE GRAPH           │ CONFIDENCE vs       │
│ Guru: x+5=12? │   (Student)──●Linear eq (0.34)    │ ACCURACY            │
│ Rahul: 17     │        │       ▲ prereq           │  [dual-line chart]  │
│ ▸ chip:       │   ●Neg numbers (0.28)  ◆adds_    │ Mastery bars        │
│  adds_instead │                           instead │ Next review: 2d     │
│ Guru: hint…   │   nodes pulse on update           │ Calibration gap     │
└───────────────┴───────────────────────────────────┴─────────────────────┘
```
- Graph: force-directed, student at centre, topics as circles sized by importance, coloured by mastery; misconceptions as purple diamonds linked to the topic they affect; prerequisite edges dashed arrows.
- Latest event gets a floating annotation: "Detected: adds instead of inverse · strength 0.35 → 0.55".
- **Demo Mode:** font +25%, hides secondary panels, shows a single large caption of the current insight for the audience.
- Bottom ribbon: "Why this question? Weakest prerequisite is negative numbers" (from the graph query). This is the "wow" explainability line.

### 3.3 Student Memory
- Left: sessions timeline. Centre: graph with time scrubber (slider replays how the graph changed). Right: "What Guru remembers" list; each item shows the source session, confidence and a trash icon.

### 3.4 Teacher Dashboard
- Class misconception heat-map (rows = misconceptions, columns = students, colour = strength) but **no ranking or scores-vs-peers**.
- "Needs support" list framed positively ("Would benefit from a negative-numbers recap").
- Summary cards (3 lines each), suggested classroom action, export PDF.

### 3.5 Parent view (mobile first)
- Language toggle at top. Three sentences in a large type. Progress ribbon (3 steps). A single "Talk to teacher" button. Nothing else.

### 3.6 Proof page
- Hero stat: **"X / 30"** in Display size with the label "synthetic students, correct misconception identified".
- Charts: tag accuracy, false-positive rate, hints-to-solve, mastery gain over 3 days.
- Separate section "Real pilot (n = 3-5, consented)": before/after cards (accuracy %, confidence 1-10).
- A visible note: "Synthetic results are not a substitute for classroom trials."

### 3.7 Privacy Center
- Toggle list of consents, list of data sources with purpose, buttons "Export my data" and "Delete everything", audit view of who accessed data.

---

## 4. Component list

`Nav`, `Hero`, `NumberedFlow`, `FeatureCard`, `LiveBadge`, `Waveform`, `TranscriptPane`, `MisconceptionChip`, `KnowledgeGraph`, `GraphLegend`, `InsightToast`, `ConfidenceAccuracyChart`, `MasteryBar`, `ReviewList`, `CalibrationGauge`, `SessionTimeline`, `MemoryList`, `ClassHeatmap`, `SummaryCard`, `ParentCard`, `LangToggle`, `StatBig`, `ConsentToggle`, `EmptyState`, `Skeleton`, `DemoModeToggle`.

**Misconception chip:** purple pill with a diamond icon + short name + strength (e.g. `adds_instead_of_inverse · 0.55`).
**Mastery bar:** 6px bar with the 3-colour scale, label `0.34`, plus text "Needs practice / Building / Strong" (do not rely on colour alone).

---

## 5. Graph visual spec (react-force-graph-2d)

| Element | Style |
|---|---|
| Student node | 14px, white ring, centre |
| Topic node | circle, radius 6-12 by importance, fill by mastery scale |
| Misconception node | diamond, `--misc`, size by strength |
| Prerequisite edge | dashed, 1px, `--line`, arrowhead |
| HOLDS edge | `--misc`, opacity by strength |
| Active (just updated) | `--accent` pulse ring, label shown |
| Labels | hidden by default; show on hover and for active node |

Performance: cap at ~80 nodes; use canvas rendering; freeze simulation after 2 s; reheat only on updates.

---

## 6. Copy bank (short, human)

- Hero: **"A tutor on a normal phone call that remembers every mistake."**
- Sub: "No app. No smartphone. Just a call."
- Flow: **Call** "Guru phones the student, in Hindi or English." · **Detect** "Finds why an answer is wrong, not just that it is." · **Remember** "Builds a memory graph of every concept and misconception." · **Recall** "Brings it back the next day, right before it fades."
- Cards: "Works on any phone." / "Memory that explains itself." / "Proof, not promises."
- Live insight: "Detected: adds instead of using the inverse."
- Parent (Hindi): "आज राहुल ने समीकरण हल करने का अभ्यास किया और पहले से बेहतर किया।"
- Safety line: "Guru never guesses feelings from a voice. Confidence is what the student tells us, plus how they perform."

---

## 7. Accessibility and quality

- WCAG AA contrast; focus rings in `--accent`; full keyboard navigation.
- Captions for all audio demos. Don't use colour alone for mastery (labels + icons).
- Mobile: single column; graph becomes a card with tap-to-expand.
- Performance: LCP < 2.5 s; lazy-load the graph; no autoplay audio.
- Empty states are helpful ("No sessions yet - run the simulator").

---

## 8. Demo screen checklist (the 2 minutes that win)

- [ ] `/live` loads in dark mode on a projector, readable from the back of the room.
- [ ] Simulator button replays the scripted Rahul session if the phone line fails.
- [ ] Graph pulse + chip appear within ~1 second of an answer.
- [ ] The "Why this question?" ribbon shows the graph-driven reason.
- [ ] Before/after card (confidence 3 → 6, mastery 0.30 → 0.62) visible at the end.
- [ ] Proof page open in a second tab with the "X / 30" number.
