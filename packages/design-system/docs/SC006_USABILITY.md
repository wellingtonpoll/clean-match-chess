# SC-006 Usability Protocol

This protocol operationalises **SC-006**: "After reading one rendered
report, a non-technical reader describes the document as analytical
or forensic, not as an anti-cheat or accusatory artefact." This
document is the canonical playbook for running and recording the
study. The doc itself MUST pass the lexical audit.

## Why this exists

The design system's structural guarantees (no red, no forbidden
vocabulary, role markers on every risk pill, monochrome glyph
fallback) target a *perception* outcome: readers should perceive the
report as forensic-analytical rather than accusatory. SC-006 is the
human-subject measurement that closes the loop on those structural
choices.

## Panel-selection rule

- **Size:** at least five (n ≥ 5) readers per study.
- **Profile:** non-technical with respect to chess.com fair-play
  policy — readers MUST NOT have prior familiarity with chess.com's
  fair-play tooling, processes, or terminology.
- **Diversity:** at least two distinct first languages across the
  panel (the lexicon ships English and Portuguese; one panel member
  per language is the minimum).
- **Conflicts:** anyone employed by, contracted to, or financially
  invested in chess.com or a competing platform is excluded.
- **Compensation:** flat per-session payment; never per-finding.

## Interview script

Read each prompt aloud verbatim. Do not paraphrase. The unprompted
response from prompts 2 and 3 is the SC-006 datum.

> 1. "Thank you for participating. I'm going to show you a printed
>    document for two minutes. Please read it as if you were a
>    journalist reading a research briefing."
>
> *(hand reader one printed report; start a two-minute timer)*
>
> 2. "In your own words, what kind of document is this?" — record
>    the answer verbatim.
>
> 3. "Who do you think wrote it, and what do you think they want
>    the reader to do with it?" — record verbatim.
>
> 4. *(only after both unprompted answers are recorded)* "Were any
>    words or phrases in the document unclear?"

## Coding word-bank

After the interview, code each unprompted answer using the
two-bucket word-bank below. The reader's response qualifies as
"analytical / forensic" if it contains at least one analytical
signal AND zero accusatory signals; otherwise it counts as a fail.

**Analytical / forensic signals** — sample anchors per language
(non-exhaustive):

| Language    | Sample anchors                                                                   |
| ----------- | -------------------------------------------------------------------------------- |
| English     | "analytical", "forensic", "statistical", "investigation", "research",            |
|             | "briefing", "report", "assessment", "diagnostic"                                 |
| Portuguese  | "analítico", "forense", "estatístico", "investigação", "pesquisa",               |
|             | "relatório", "avaliação", "diagnóstico"                                          |

**Accusatory signals.** Do not inline the trigger lexicon in this
document. The canonical source of accusatory triggers is the
forbidden-terms file shipped with feature 001:

- English: `tests/fixtures/forbidden-terms/en.txt`
- Portuguese: `tests/fixtures/forbidden-terms/pt.txt`

Each row of those TSV files is a `term<TAB>category<TAB>match_mode`
triple. For SC-006 coding, treat any reader's spontaneous answer
that contains **any** term from those files (with the listed match
mode) as carrying an accusatory signal. The protocol script
[`scripts/sc006_code_response.py`](../../../scripts/sc006_code_response.py)
(deferred; out of scope for v1.0.0) will automate this match later.

Rationale: storing the trigger list externally keeps this protocol
lexically clean (it can ship through the same audit pipeline as a
rendered report) while letting the coder consult the authoritative
list at session time.

## Pass / fail criterion

- **Per reader:** pass iff the unprompted answer contains ≥ 1
  analytical signal AND 0 accusatory signals.
- **Per study:** pass iff ≥ 4 of 5 readers pass (≥ 80 %). At least one
  Portuguese-language session MUST pass.

## Tally template

Record raw + coded results in
[`SC006_RESULTS.md`](SC006_RESULTS.md) using the schema:

```markdown
## Study YYYY-MM-DD

| Reader id | Language | Unprompted answer (verbatim) | Analytical signals | Accusatory signals | Pass |
| --------- | -------- | ---------------------------- | ------------------ | ------------------ | ---- |
| R-01      | en       | "..."                        | "analytical"       | —                  | yes  |
| R-02      | pt       | "..."                        | "relatório"        | —                  | yes  |
| ...       |          |                              |                    |                    |      |

**Outcome:** PASS / FAIL — N / 5 readers met the criterion.
```

## When to re-run the study

- Before every MAJOR design-system release.
- After any forbidden-terms list change that touches the
  `accusation` or `outcome` categories.
- After any wording change to the `Narrative.summary_paragraph`
  template.
- Whenever a session's outcome is FAIL — schedule the next study
  within four weeks and document the wording / structure change in
  the interim.

## Cross-feature references

- Lexicon entries: `src/design_system/lexicon/entries_{en,pt}.json`
- Forbidden terms: `tests/fixtures/forbidden-terms/{en,pt}.txt`
- Lexical audit: `src/design_system/audits/lexical.py`
- Risk-pill role contract: `contracts/audit-palette.md` § Track C
- Headline-metric role contract: `contracts/audit-typography.md`
  § "Headline metric definition"
