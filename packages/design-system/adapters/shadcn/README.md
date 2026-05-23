# shadcn/ui adapter

Phase-3 placeholder. When `apps/frontend` lands:

1. Generate the Tailwind theme: `uv run python -m design_system.tokens.compile_tailwind`.
2. Wire shadcn primitives to consume the design-system tokens
   (colour, radius, spacing, typography).
3. Override risk-pill / analytical-card / heuristic-badge variants
   using the locked `RiskTreatment` recipes from
   `design_system.components.risk_treatments`.
4. Run `python -m design_system.audits.palette` and the dynamic
   motion audit (env-gated by `CLEANMATCH_WEB_AUDIT=1`) against
   the rendered DOM before merging.

The four design-system audits MUST stay green for every shadcn
component variant.
