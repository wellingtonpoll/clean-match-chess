# Contract: Motion Audit

**Maps to**: FR-005, FR-014, SC-004 of the design-system spec.

## Purpose

Guarantee that every animated transition on every user-facing web
surface (a) lasts between 200 and 350 ms inclusive, (b) uses the locked
easing curve `cubic-bezier(0.22, 1, 0.36, 1)`, and (c) collapses to 0 ms
when the user/OS requests `prefers-reduced-motion`.

## Scope

- **Web** (Phase 3 frontend): full audit.
- **HTML report**: PDF and HTML report artefacts have no JS-driven
  animations, but the audit still verifies the generated CSS contains
  no `transition` or `animation` rules outside the locked tokens.
- **PDF**: no-op pass (PDFs are static).

## Web audit method

Runs in Playwright (Phase 3). Instruments
`window.requestAnimationFrame` to capture every transition's first and
last frame timestamps.

```python
from design_system.audits.motion import audit_web

result = audit_web(
    base_url="http://localhost:3000",
    paths=["/dashboard", "/audit/<sample-run-id>", "/account/<sample>"],
    tokens=load_tokens(),
)
```

Behaviour:
1. Load each path in Playwright headless.
2. Trigger every documented interaction (hover, focus, open modal,
   change tab) — driven by `paths` + a tag-based interaction inventory
   in `packages/design-system/src/design_system/audits/motion_interactions.py`.
3. For every captured transition:
   - Duration MUST be in `[200, 350]` ms. Failures use rule
     `motion_out_of_range`.
   - Easing MUST match the locked cubic-bezier curve to four decimal
     places. Failures use rule `motion_wrong_easing`.
4. Re-run with `prefers-reduced-motion: reduce` enabled. Every
   transition MUST measure 0 ms. Failures use rule
   `motion_ignored_reduced_motion`.

## HTML/PDF static-CSS audit method

```python
from design_system.audits.motion import audit_static_css

result = audit_static_css(css_path="adapters/weasyprint/tokens.css")
```

Behaviour:
1. Parse the CSS with `tinycss2`.
2. Every `transition` and `animation` declaration MUST reference only
   token-derived values. Literal `linear`, `ease-in`, etc. → fail with
   rule `motion_wrong_easing`. Literal durations outside the locked
   tokens → fail with rule `motion_out_of_range`.

## Override discipline

An exception list at
`packages/design-system/src/design_system/audits/motion_overrides.json`
allows documented exemptions. Each entry requires: file, selector,
reason, reviewer GitHub handle, expiry ISO date. Expired entries fail
the audit.

## Return shape

```python
class MotionAuditReport:
    audit_name: Literal["motion"]
    artefact: str
    static_findings: list[AuditFinding]
    dynamic_findings: list[AuditFinding]
    reduced_motion_findings: list[AuditFinding]
    status: Literal["pass", "fail"]
```

## Performance budget

- Static CSS audit: ≤ 100 ms.
- Web instrumented audit: ≤ 60 s for the full path inventory (Phase 3
  only; deferred).

## CI wiring

```python
@pytest.mark.audit_motion(artefact="adapters/weasyprint/tokens.css")
def test_static_css_motion(): ...

# Phase 3 only:
@pytest.mark.audit_motion(artefact="web:dashboard")
def test_web_motion(playwright_session): ...
```

## Exit semantics

| Exit code | Meaning |
|---|---|
| 0 | Audit passes |
| 1 | Token/range/easing violation (CI-blocking) |
| 2 | Artefact unreachable (e.g., dev server down for web mode) |
| 3 | Internal bug |
