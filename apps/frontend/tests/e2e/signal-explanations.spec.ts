// Feature 006 / T015 — SC-002 binary criteria: every signal has an entry,
// pt-BR text, no jargon-blacklisted terms. Pure module test, no page.

import { test, expect } from '@playwright/test'
import {
  SIGNAL_EXPLANATIONS,
  FALLBACK_EXPLANATION,
  JARGON_BLACKLIST,
  explainSignal,
} from '../../lib/signalExplanations'

test.describe('SC-002 — signal explanations binary criteria', () => {
  test('every SignalName has a non-empty entry', () => {
    const entries = Object.entries(SIGNAL_EXPLANATIONS)
    expect(entries.length).toBe(11)
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
})
