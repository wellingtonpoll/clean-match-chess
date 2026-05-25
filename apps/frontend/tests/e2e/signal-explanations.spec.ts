// Feature 006 / T015 — SC-002 binary criteria: every signal has an entry,
// pt-BR text, no jargon-blacklisted terms. Pure module test, no page.

import { test, expect } from '@playwright/test'
import {
  SIGNAL_EXPLANATIONS,
  FALLBACK_EXPLANATION,
  JARGON_BLACKLIST,
  explainSignal,
  summarizeGame,
} from '../../lib/signalExplanations'

test.describe('SC-002 — signal explanations binary criteria', () => {
  test('every SignalName has a non-empty entry', () => {
    const entries = Object.entries(SIGNAL_EXPLANATIONS)
    // Headcount enforced so a removed signal name does not silently drop
    // coverage. Bump intentionally when adding / removing entries.
    expect(entries.length).toBe(15)
    for (const [name, copy] of entries) {
      expect(copy.headline.length, `${name}.headline non-empty`).toBeGreaterThan(0)
      expect(copy.body.length, `${name}.body non-empty`).toBeGreaterThan(0)
    }
  })

  test('no entry uses blacklisted jargon', () => {
    for (const [name, copy] of Object.entries(SIGNAL_EXPLANATIONS)) {
      for (const pat of JARGON_BLACKLIST) {
        expect(copy.body, `${name}.body matches forbidden pattern ${pat}`).not.toMatch(pat)
        expect(copy.headline, `${name}.headline matches forbidden pattern ${pat}`).not.toMatch(pat)
      }
    }
  })

  test('explainSignal returns fallback for unknown signal', () => {
    const got = explainSignal('totally-unknown-signal')
    expect(got).toBe(FALLBACK_EXPLANATION)
  })

  test('explainSignal returns specific entry for known signal', () => {
    const got = explainSignal('acpl-analysis')
    expect(got).toBe(SIGNAL_EXPLANATIONS['acpl-analysis'])
    expect(got.headline).toBe('Precisão acima do esperado')
  })

  test('namespaced + bare signal names resolve to the same copy', () => {
    expect(explainSignal('behavioral-patterns/precision-burst').headline).toBe(
      explainSignal('precision-burst').headline
    )
    expect(explainSignal('complexity-analysis').headline).toBe(
      explainSignal('complexity').headline
    )
    expect(explainSignal('engine-correlation/weighted').headline).toBe(
      explainSignal('engine-correlation/weighted-top1').headline
    )
  })
})

test.describe('summarizeGame — per-game reasoning narrative', () => {
  test('quotes the actual numeric score in the intro', () => {
    const s = summarizeGame({ score: 0.457, riskLevel: 'medium', dominantSignals: ['x'] })
    expect(s.intro).toContain('45.7%')
  })

  test('headline + verdict vary by risk_level', () => {
    const high = summarizeGame({ score: 0.83, riskLevel: 'high' })
    const med = summarizeGame({ score: 0.45, riskLevel: 'medium' })
    const low = summarizeGame({ score: 0.08, riskLevel: 'low' })
    expect(high.headline).toMatch(/alto/i)
    expect(med.headline).toMatch(/intermedi/i)
    expect(low.headline).toMatch(/baixo/i)
    expect(high.intro).not.toBe(med.intro)
    expect(med.intro).not.toBe(low.intro)
  })

  test('signal lead-in differs for empty vs populated dominant signals', () => {
    const empty = summarizeGame({ score: 0.12, riskLevel: 'low', dominantSignals: [] })
    const populated = summarizeGame({
      score: 0.45,
      riskLevel: 'medium',
      dominantSignals: ['a', 'b', 'c'],
    })
    expect(empty.signalsLeadIn).toMatch(/Nenhum sinal/i)
    expect(populated.signalsLeadIn).toContain('3')
  })

  test('confidence-interval phrase labels width buckets', () => {
    const narrow = summarizeGame({
      score: 0.45,
      riskLevel: 'medium',
      confidenceInterval: [0.43, 0.47],
    })
    const wide = summarizeGame({
      score: 0.45,
      riskLevel: 'medium',
      confidenceInterval: [0.2, 0.7],
    })
    expect(narrow.intro).toMatch(/precisão alta/i)
    expect(wide.intro).toMatch(/incerteza/i)
  })
})
