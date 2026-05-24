#!/usr/bin/env bash
# Manual smoke test for clean-match-chess CLI
# Usage: ./test-manual.sh
# Output: results + exported files in /tmp/cleanmatch-test/

set -euo pipefail

OUTDIR="/tmp/cleanmatch-test"
PASS=0
FAIL=0

green()  { printf '\033[32m%s\033[0m\n' "$*"; }
red()    { printf '\033[31m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
header() { printf '\n\033[1;34m══ %s ══\033[0m\n' "$*"; }
check()  {
  local label="$1"; shift
  if "$@" &>/dev/null; then
    green "  ✓ $label"
    PASS=$((PASS + 1))
  else
    red   "  ✗ $label"
    FAIL=$((FAIL + 1))
  fi
}

mkdir -p "$OUTDIR"

# ── 1. CLI help ───────────────────────────────────────────────────────────────
header "1. CLI — help"
uv run cleanmatch --help

# ── 2. Audit clean games ──────────────────────────────────────────────────────
header "2. audit-game — known clean"

echo ""
yellow "  → Anderssen vs Kieseritzky (1851)"
ANDERSSEN=$(uv run cleanmatch audit-game \
  tests/fixtures/pgn/known-clean/anderssen-vs-kieseritzky-1851.pgn)
echo "$ANDERSSEN"
ANDERSSEN_ID=$(echo "$ANDERSSEN" | grep run_id | awk '{print $2}')

echo ""
yellow "  → Morphy vs Allies (1858)"
MORPHY=$(uv run cleanmatch audit-game \
  tests/fixtures/pgn/known-clean/morphy-vs-allies-1858.pgn)
echo "$MORPHY"
MORPHY_ID=$(echo "$MORPHY" | grep run_id | awk '{print $2}')

# ── 3. Audit suspect games ────────────────────────────────────────────────────
header "3. audit-game — known suspect"

echo ""
yellow "  → Synthetic full-engine"
FULL_ENGINE=$(uv run cleanmatch audit-game \
  tests/fixtures/pgn/known-suspect/synthetic-full-engine.pgn)
echo "$FULL_ENGINE"
ENGINE_ID=$(echo "$FULL_ENGINE" | grep run_id | awk '{print $2}')

echo ""
yellow "  → Synthetic selective assistance"
SELECTIVE=$(uv run cleanmatch audit-game \
  tests/fixtures/pgn/known-suspect/synthetic-selective-assistance.pgn)
echo "$SELECTIVE"
SELECTIVE_ID=$(echo "$SELECTIVE" | grep run_id | awk '{print $2}')

# ── 4. show (move timeline) ───────────────────────────────────────────────────
header "4. show — move-by-move timeline"

echo ""
yellow "  → Anderssen ($ANDERSSEN_ID)"
uv run cleanmatch show "$ANDERSSEN_ID"

echo ""
yellow "  → Full-engine ($ENGINE_ID)"
uv run cleanmatch show "$ENGINE_ID"

# ── 5. export ─────────────────────────────────────────────────────────────────
header "5. export — all formats"

echo ""
yellow "  → HTML"
uv run cleanmatch export "$ANDERSSEN_ID" \
  --format html --out "$OUTDIR/anderssen.html" 2>/dev/null
check "HTML generated ($OUTDIR/anderssen.html)" test -s "$OUTDIR/anderssen.html"

echo ""
yellow "  → JSON"
uv run cleanmatch export "$ANDERSSEN_ID" \
  --format json --out "$OUTDIR/anderssen.json" 2>/dev/null
check "JSON generated ($OUTDIR/anderssen.json)" test -s "$OUTDIR/anderssen.json"

echo ""
yellow "  → Bundle (zip with PDF+HTML+JSON+manifest)"
uv run cleanmatch export "$ANDERSSEN_ID" \
  --out "$OUTDIR/anderssen.bundle" 2>/dev/null
check "Bundle generated ($OUTDIR/anderssen.bundle)" test -s "$OUTDIR/anderssen.bundle"

if python3 -c "
import zipfile, sys
z = zipfile.ZipFile('$OUTDIR/anderssen.bundle')
names = z.namelist()
required = {'report.pdf', 'report.html', 'report.json', 'manifest.json', 'README.txt'}
missing = required - set(names)
if missing:
    print('Missing:', missing); sys.exit(1)
print('Bundle contents:', ', '.join(sorted(names)))
"; then
  check "Bundle contains all required files" true
else
  check "Bundle contains all required files" false
fi

echo ""
yellow "  → JSON content preview"
python3 -m json.tool "$OUTDIR/anderssen.json" | head -20

# ── 6. Automated quality gates ────────────────────────────────────────────────
header "6. Quality gates"

echo ""
yellow "  → ruff check"
check "ruff check" uv run ruff check .

yellow "  → ruff format"
check "ruff format --check" uv run ruff format --check .

yellow "  → mypy"
check "mypy --strict" uv run mypy

yellow "  → pytest (coverage ≥ 85%)"
check "pytest --cov-fail-under=85" \
  uv run pytest --cov --cov-fail-under=85 -q --tb=no

# ── 7. py.typed + __all__ spot checks ────────────────────────────────────────
header "7. Package hygiene"

for pkg in \
  "packages/analysis-core/src/analysis_core" \
  "packages/design-system/src/design_system" \
  "packages/heuristics/src/heuristics" \
  "packages/report-engine/src/report_engine" \
  "packages/shared-types/src/shared_types" \
  "apps/cli/src/cleanmatch_cli"; do
  name=$(basename "$pkg")
  check "py.typed in $name" test -f "$pkg/py.typed"
  check "__all__ in $name/__init__.py" \
    grep -q "__all__" "$pkg/__init__.py"
done

# ── 8. CI hygiene ─────────────────────────────────────────────────────────────
header "8. CI supply-chain"

MUTABLE=$(grep "uses:" .github/workflows/ci.yml \
  | grep -v "@[0-9a-f]\{40\}" || true)
if [ -z "$MUTABLE" ]; then
  check "All uses: lines SHA-pinned" true
else
  echo "  Mutable tags found:"
  echo "$MUTABLE"
  check "All uses: lines SHA-pinned" false
fi

check "permissions: in ci.yml (≥4 blocks)" \
  bash -c '[ "$(grep -c "permissions:" .github/workflows/ci.yml)" -ge 4 ]'

check "No || true in ci.yml" \
  bash -c '! grep -q "|| true" .github/workflows/ci.yml'

check ".github/dependabot.yml exists" test -f .github/dependabot.yml
check ".github/CODEOWNERS exists"     test -f .github/CODEOWNERS
check ".github/PULL_REQUEST_TEMPLATE.md exists" \
  test -f .github/PULL_REQUEST_TEMPLATE.md
check "CONTRIBUTING.md exists"        test -f CONTRIBUTING.md
check "CHANGELOG.md exists"           test -f CHANGELOG.md
check "LICENSE exists"                test -f LICENSE

# ── Summary ───────────────────────────────────────────────────────────────────
header "Summary"
echo ""
echo "  Output files: $OUTDIR/"
ls -lh "$OUTDIR/"
echo ""
if [ "$FAIL" -eq 0 ]; then
  green "  ALL CHECKS PASSED ($PASS/$((PASS + FAIL)))"
else
  red   "  $FAIL FAILED, $PASS passed"
  exit 1
fi
