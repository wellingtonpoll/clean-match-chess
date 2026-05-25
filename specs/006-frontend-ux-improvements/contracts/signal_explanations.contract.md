# Signal Explanations Contract — Feature 006

**Branch**: `006-frontend-ux-improvements`

Shape, content rules, and lookup semantics of `apps/frontend/lib/signalExplanations.ts`. Consumed by `ExpandedAnalysis` component (US2).

---

## Module API

```ts
// apps/frontend/lib/signalExplanations.ts

export interface ExplanationCopy {
  headline: string;
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
export const FALLBACK_EXPLANATION: ExplanationCopy;
export const JARGON_BLACKLIST: readonly RegExp[];

export function explainSignal(name: string): ExplanationCopy;
```

---

## Field rules

### `headline`

- 3-5 words.
- pt-BR.
- No technical jargon.
- Examples: "Precisão acima do esperado", "Lances batem com o motor", "Mudança brusca de estilo".

### `body`

- 1-2 sentences.
- pt-BR.
- Plain language; describes what the signal measures and why high values are suspect.
- MUST NOT match any pattern in `JARGON_BLACKLIST`.
- MAY use technical terms IF they are immediately explained inline (e.g., "centipawn (centésimo de peão)").

---

## Jargon blacklist (enforced by test)

```ts
export const JARGON_BLACKLIST: readonly RegExp[] = [
  /\bz-?score\b/i,
  /\bbootstrap\b/i,
  /\bCUSUM\b/i,
  /\bp-?value\b/i,
  /\bratio\b(?!\s+(entre|de))/i,
  /\bregression residual\b/i,
  /\bbucket\b(?!\s+de\s+rating)/i,
];
```

A test (`signal-explanations.spec.ts`) iterates `Object.values(SIGNAL_EXPLANATIONS).map(e => e.body)` and asserts none match any regex.

---

## Lookup semantics

```ts
export function explainSignal(name: string): ExplanationCopy {
  if (name in SIGNAL_EXPLANATIONS) {
    return SIGNAL_EXPLANATIONS[name as SignalName];
  }
  return FALLBACK_EXPLANATION;
}
```

- Constant-time `O(1)` lookup.
- Pure: no I/O, no async, no side effects.
- Unknown signal names route to `FALLBACK_EXPLANATION` (FR-005 / US2 AS5).

---

## Adding a new signal

When the backend emits a new signal name not in `SignalName`:

1. Add the name to the `SignalName` union.
2. Add an entry to `SIGNAL_EXPLANATIONS`.
3. Ensure body passes the jargon blacklist test.
4. Update `quickstart.md §3` if the addition affects user-facing copy in a non-trivial way.

Until step 1-3 land, the fallback handles the new signal gracefully (no UI crash; user sees a generic "Sinal técnico" entry).

---

## Test surface

`apps/frontend/tests/e2e/signal-explanations.spec.ts` (NOT colocated under `lib/` because Playwright is the test runner). Assertions:

```ts
test("every SignalName has an entry", () => {
  for (const name of Object.keys(SIGNAL_EXPLANATIONS)) {
    expect(SIGNAL_EXPLANATIONS[name].headline.length).toBeGreaterThan(0);
    expect(SIGNAL_EXPLANATIONS[name].body.length).toBeGreaterThan(0);
  }
});

test("no entry uses blacklisted jargon", () => {
  for (const [name, copy] of Object.entries(SIGNAL_EXPLANATIONS)) {
    for (const pat of JARGON_BLACKLIST) {
      expect(copy.body, `${name}.body matches ${pat}`).not.toMatch(pat);
    }
  }
});

test("fallback returned for unknown signal", () => {
  const got = explainSignal("totally-unknown-signal");
  expect(got).toBe(FALLBACK_EXPLANATION);
});
```

This test target satisfies the reworked SC-002 acceptance.
