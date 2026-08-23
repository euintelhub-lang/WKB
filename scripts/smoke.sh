#!/usr/bin/env bash
# Smoke test for wkb.py — exercises seal/check/ls/bridge against real records
# in a throwaway directory, asserting on the actual output of each command.
# Run locally: bash scripts/smoke.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WKB="python3 $REPO_ROOT/wkb.py"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

extract_id() { grep -oE 'id=[a-z0-9-]+' | cut -d= -f2; }

# 1. seal + check a simple record
out=$($WKB seal --type decision --topic "smoke: simple" --body "kratko tqlo")
id=$(echo "$out" | extract_id)
$WKB check "records/$id.md" | grep -q "^PASS" || fail "check did not PASS a freshly sealed record"
pass "seal + check"

# 2. bridge --target json on a simple record -> SUCCESS, lossless
$WKB bridge "records/$id.md" --target json | grep -q "^status: SUCCESS" || fail "json bridge was not SUCCESS"
pass "bridge json -> SUCCESS"

# 3. bridge --target csv with 2 parents + long multiline body -> DEGRADED, 3 reasons
out2=$($WKB seal --type decision --topic "smoke: child A" --body "a")
id2=$(echo "$out2" | extract_id)
long_body=$(python3 -c "print('line of text.\n' * 15, end='')")
out3=$($WKB seal --type observation --topic "smoke: multi-parent" \
  --parent "$id" --parent "$id2" --raw "provenance note" --body "$long_body")
id3=$(echo "$out3" | extract_id)

csv_result=$($WKB bridge "records/$id3.md" --target csv)
echo "$csv_result" | grep -q "^status: DEGRADED" || fail "csv bridge was not DEGRADED"
echo "$csv_result" | grep -q "parent: LOSSY_ENCODING" || fail "csv bridge missing parent/LOSSY_ENCODING"
echo "$csv_result" | grep -q "body: LOSSY_ENCODING" || fail "csv bridge missing body/LOSSY_ENCODING"
echo "$csv_result" | grep -q "body: CONSTRAINT_EXCEEDED" || fail "csv bridge missing body/CONSTRAINT_EXCEEDED"
pass "bridge csv -> DEGRADED (3 reasons)"

# 4. bridge --target xml (unknown format) -> DEGRADED, generic fallback, raw dropped
xml_result=$($WKB bridge "records/$id3.md" --target xml)
echo "$xml_result" | grep -q "^status: DEGRADED" || fail "xml bridge was not DEGRADED"
echo "$xml_result" | grep -q "raw: NO_TARGET_EQUIVALENT" || fail "xml bridge did not drop raw as NO_TARGET_EQUIVALENT"
pass "bridge unknown-format -> generic fallback"

# 5. tampered record -> FAILED (bridge refuses to translate an unverified record)
cp "records/$id.md" tampered.md
sed -i 's/kratko/PROMENENO/' tampered.md
tampered_result=$($WKB bridge tampered.md --target json || true)
echo "$tampered_result" | grep -q "^status: FAILED" || fail "tampered record was not rejected as FAILED"
pass "bridge on tampered record -> FAILED"

# 6. ls sanity
$WKB ls | grep -q "$id" || fail "ls is missing a sealed record"
pass "ls"

echo "ALL SMOKE TESTS PASSED"
