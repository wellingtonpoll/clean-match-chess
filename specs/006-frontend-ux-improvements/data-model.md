# Data Model — Feature 006 (Frontend UX Improvements)

**Branch**: `006-frontend-ux-improvements` | **Date**: 2026-05-24

Frontend-only models. No backend schema changes (FR-017). All entities live under `apps/frontend/`.

---

## 1. `SignalExplanation` (new — `apps/frontend/lib/signalExplanations.ts`)

**Type**:

```ts
export interface ExplanationCopy {
  /** 3-5 word lay-friendly title. */
  headline: string;
  /** 1-2 sentence pt-BR body. No jargon from the blacklist. */
  body: string;
}

export type SignalName =
  | "acpl-analysis"
  | "engine-correlation/top1"
  | "engine-correlation/top3"
  | "engine-correlation/weighted-top1"
  | "regime-shift"
  | "timing-analysis"
  | "blunder-suppression"
  | "precision-burst"
  | "complexity"
  | "tactical-detection"
  | "segments-weighted-aggregate";

export const SIGNAL_EXPLANATIONS: Record<SignalName, ExplanationCopy>;

export function explainSignal(name: string): ExplanationCopy;
```

**Fallback** (returned by `explainSignal` for unknown signal names per FR-005 / US2 AS5):

```ts
const FALLBACK: ExplanationCopy = {
  headline: "Sinal técnico",
  body: "Indicador estatístico identificado pelo motor de análise. Descrição leiga não disponível para este sinal.",
};
```

**Jargon blacklist** (used by the unit test `signal-explanations.spec.ts`):

```ts
export const JARGON_BLACKLIST: readonly RegExp[] = [
  /\bz-?score\b/i,
  /\bbootstrap\b/i,
  /\bCUSUM\b/i,
  /\bp-?value\b/i,
  /\bratio\b(?!\s+(entre|de))/i,  // allow "razão entre A e B"
  /\bregression residual\b/i,
  /\bbucket\b(?!\s+de\s+rating)/i,
];
```

**Validation** (covered by `signal-explanations.spec.ts`):
- Every key in `SignalName` union has an entry in `SIGNAL_EXPLANATIONS`.
- Every `body` string passes `Intl`-detection or contains pt-BR-typical characters (`ç`, `ã`, `õ`, etc.) OR is explicitly tagged with `lang="pt-BR"`.
- No entry's `body` matches any blacklist regex.

---

## 2. `PlayerLink` props (new component `apps/frontend/components/PlayerLink.tsx`)

```ts
interface PlayerLinkProps {
  /** Display username from PGN headers (White or Black). */
  username: string;
  /** True if this username equals the currently-active audit subject — render as non-clickable text. */
  isSubject: boolean;
  /** Aria label override for screen readers. Defaults to `Analisar partidas de ${username}`. */
  ariaLabel?: string;
}
```

**Behavior**:
- `isSubject === true` → renders `<span>` with a subdued style (text only, not interactive). No event handlers.
- `isSubject === false` → renders `<button type="button">` with click handler that calls `useAnalysisContext().runAnalysis(0, { newUsername: username })`.
- `disabled` automatically when `useAnalysisContext().isAnalyzing && username === useAnalysisContext().activeUsername` (defensive; should be rare given `isSubject` guard).

---

## 3. `ExpandableCardState` (in-place state on existing `GameRow`)

**Type**: local React state per `GameRow` instance.

```ts
const [expanded, setExpanded] = useState(false);
```

**Constraints**:
- Only togglable when `game.status === "done"` (per FR-004; clicks on `pending`/`analyzing`/`error` cards do nothing).
- Per FR-007, each card's state is independent; **no parent coordination**.
- Renders `<button aria-expanded={expanded} aria-controls={`expanded-${game.runId}`}>` wrapper around the row's clickable area.
- Expanded section uses `id={`expanded-${game.runId}`}` and includes the `ExpandedAnalysis` sub-component.

**Animation**: CSS-only collapse/expand using `height: auto` + `max-height` transition OR `display: none`/`block` (no JS measurement). Decision: `display: none` initially → render conditionally. Animation polish (slide-down) is nice-to-have, not required by SC-008 (SC-008 is about *settled* layout shift, not transitions).

---

## 4. `ExpandedAnalysis` props (new component `apps/frontend/components/ExpandedAnalysis.tsx`)

```ts
interface ExpandedAnalysisProps {
  /** Game result with at least dominantSignals populated. */
  game: GameResult;  // existing type from GameRow.tsx
}
```

**Render**:

```tsx
<div className="expanded-analysis">
  <div className="expanded-analysis__label">Análise detalhada</div>
  <ul>
    {(game.dominantSignals ?? []).map((sig) => {
      const exp = explainSignal(sig);
      return (
        <li key={sig}>
          <strong>{exp.headline}</strong>
          <p>{exp.body}</p>
        </li>
      );
    })}
    {(!game.dominantSignals || game.dominantSignals.length === 0) && (
      <li className="expanded-analysis__empty">Nenhum sinal específico predominou neste score.</li>
    )}
  </ul>
</div>
```

---

## 5. `Header` component (new — `apps/frontend/components/Header.tsx`)

```ts
interface HeaderProps {
  /** Brand click handler (default = reset analyses). */
  onBrandClick?: () => void;
}
```

**Behavior**:
- Renders sticky header (per R4): `position: fixed` + brand left + search form right (desktop) or stacked (mobile <480px).
- Consumes `useAnalysisContext()` for `username`, `setUsername`, `platform`, `setPlatform`, `isAnalyzing`, `runAnalysis`.
- Brand click calls `onBrandClick ?? defaultReset` where `defaultReset` clears sessions + aborts in-flight analysis.

**Layout via CSS**:

```css
/* Desktop ≥ 768px */
.header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  height: var(--header-h-desktop, 64px);
}

/* Mobile < 480px */
@media (max-width: 479px) {
  .header {
    flex-direction: column;
    height: auto;
    --header-h-mobile: 112px;
  }
}
```

Main content's `padding-top` matches `--header-h-{desktop,mobile}` via the same media query.

---

## 6. `AnalysisContext` (new — internal, lives in `apps/frontend/app/page.tsx` or `lib/`)

```ts
interface AnalysisContextValue {
  // existing state surfaced
  username: string;
  setUsername: (u: string) => void;
  platform: "chesscom" | "lichess";
  setPlatform: (p: "chesscom" | "lichess") => void;
  sessions: Session[];
  isAnalyzing: boolean;
  activeUsername: string;

  // actions
  runAnalysis: (offset: number, opts?: { newUsername?: string }) => Promise<void>;
  reset: () => void;
}

export const AnalysisContext: React.Context<AnalysisContextValue | null>;
export function useAnalysisContext(): AnalysisContextValue;  // throws if used outside provider
```

`runAnalysis` accepts an optional `newUsername`. When supplied, it overrides the current `username` for this invocation AND syncs back into `setUsername` so the Header reflects it.

`reset` aborts any in-flight analysis, clears `sessions`, clears `activeUsername`, and clears `username`. Called by:
- Header brand click (default behavior per Clarifications).
- Test scenarios that need a clean state.

---

## 7. Playwright fixture file format (new — `apps/frontend/tests/e2e/fixtures/`)

Plain-text SSE response payload, one `data:` line per game event, ending with `data: {"done": true}`. Helper `mockStream(page, scenarioName)` reads the file, sets `Content-Type: text/event-stream`, and pipes through Playwright's route interception.

**Scenarios shipped**:
- `clean-3-games.txt` — 3 games, all low score, no expanded content needed.
- `mixed-5-games.txt` — 5 games, mix of risk levels, one high-score with 2 dominant signals.
- `suspect-1-game.txt` — single high-suspicion game with 3 dominant signals (worst-case expanded layout).
- `error-upstream.txt` — single `data: {"error": "upstream_unavailable"}` payload.

---

## Entities Inventory (cross-reference vs feature 004/005)

| Entity | Layer | Phase 1 (004) | Phase 2 (005) | Phase 3 web UI (006) |
|---|---|---|---|---|
| `GameResult` (frontend) | client | exists | unchanged | unchanged — consumed by new components |
| `Session` (frontend) | client | exists | unchanged | unchanged |
| `SignalAggregate` (backend) | shared | exists | unchanged | unchanged |
| `SignalExplanation` | client | does not exist | does not exist | **NEW** |
| `PlayerLink` | client component | does not exist | does not exist | **NEW** |
| `ExpandedAnalysis` | client component | does not exist | does not exist | **NEW** |
| `Header` | client component | does not exist | does not exist | **NEW** |
| `AnalysisContext` | client | does not exist | does not exist | **NEW** |
