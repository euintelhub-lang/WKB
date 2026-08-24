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

# 7. bridge --target restore: two-hop parent chain -> SUCCESS, lineage in order
out4=$($WKB seal --type decision --topic "restore: child" --parent "$id3" --body "restore target smoke test")
id4=$(echo "$out4" | extract_id)
restore_result=$($WKB bridge "records/$id4.md" --target restore)
echo "$restore_result" | grep -q "^status: SUCCESS" || fail "restore bridge (full chain) was not SUCCESS"
echo "$restore_result" | grep -q "\[$id\]" || fail "restore bridge lineage is missing grandparent $id"
echo "$restore_result" | grep -q "\[$id2\]" || fail "restore bridge lineage is missing grandparent $id2"
echo "$restore_result" | grep -q "\[$id3\]" || fail "restore bridge lineage is missing immediate parent $id3"
pass "bridge restore -> SUCCESS (3-node lineage resolved)"

# 8. bridge --target restore: missing parent -> DEGRADED, LOSSY_ENCODING
out5=$($WKB seal --type decision --topic "restore: orphan" --parent "wkb-20260101-dead" --body "parent was never sealed")
id5=$(echo "$out5" | extract_id)
orphan_result=$($WKB bridge "records/$id5.md" --target restore)
echo "$orphan_result" | grep -q "^status: DEGRADED" || fail "restore bridge (missing parent) was not DEGRADED"
echo "$orphan_result" | grep -q "parent: LOSSY_ENCODING" || fail "restore bridge missing parent/LOSSY_ENCODING"
pass "bridge restore -> DEGRADED (missing ancestor)"

# 9. dispatch: two agreeing providers -> AGREE
agree_out=$($WKB dispatch --topic "smoke: agree" --provider "a=echo same" --provider "b=echo same")
echo "$agree_out" | grep -q "^verdict: AGREE" || fail "dispatch did not report AGREE for identical provider output"
pass "dispatch -> AGREE"

# 10. dispatch: two disagreeing providers -> DISAGREE, both texts preserved
disagree_out=$($WKB dispatch --topic "smoke: disagree" --provider "a=echo one" --provider "b=echo two")
echo "$disagree_out" | grep -q "^verdict: DISAGREE" || fail "dispatch did not report DISAGREE for differing provider output"
echo "$disagree_out" | grep -q "^one$" || fail "dispatch lost provider a's text"
echo "$disagree_out" | grep -q "^two$" || fail "dispatch lost provider b's text"
pass "dispatch -> DISAGREE (both positions preserved)"

# 11. dispatch: a failing provider surfaces the error, doesn't crash
broken_exit=0
$WKB dispatch --topic "smoke: broken" --provider "bad=exit 1" >/dev/null 2>&1 || broken_exit=$?
[ "$broken_exit" -eq 2 ] || fail "dispatch did not exit 2 on a failing provider (got $broken_exit)"
pass "dispatch -> error on failing provider"

# 12. dispatch --seal: produces a real, checkable WKB record
$WKB dispatch --topic "smoke: seal" --provider "a=echo x" --provider "b=echo y" --seal >/dev/null
dispatch_id=$(ls -t records/*.md | head -1)
$WKB check "$dispatch_id" | grep -q "^PASS" || fail "sealed dispatch record did not pass check"
pass "dispatch --seal -> real checkable record"

# 13. dispatch: providers run concurrently, not sequentially. Three
# providers each sleep 1s; sequential execution would take >=3s, parallel
# should land well under 3s. Timed with the shell builtin, not `time`
# piped through anything, so the measurement can't be swallowed.
start=$(date +%s)
$WKB dispatch --topic "smoke: concurrency" \
  --provider "a=sleep 1 && echo a" \
  --provider "b=sleep 1 && echo b" \
  --provider "c=sleep 1 && echo c" >/dev/null
elapsed=$(( $(date +%s) - start ))
[ "$elapsed" -lt 3 ] || fail "dispatch took ${elapsed}s for 3x 1s providers -- not running concurrently"
pass "dispatch -> providers run concurrently (${elapsed}s for 3x 1s providers)"

# 14. dispatch: audit log records every provider attempt, including a
# failing one -- even though dispatch() raises and the run never reaches
# a verdict. This is the point of the audit trail: it survives what the
# AGREE/DISAGREE snapshot alone cannot show.
rm -f records/dispatch_audit.jsonl
$WKB dispatch --topic "smoke: audit ok" --provider "a=echo x" --provider "b=echo y" >/dev/null
[ "$(wc -l < records/dispatch_audit.jsonl)" -eq 2 ] || fail "audit log did not gain one line per successful provider"
grep -q '"outcome": "success"' records/dispatch_audit.jsonl || fail "audit log missing success outcome"

$WKB dispatch --topic "smoke: audit fail" --provider "bad=exit 1" >/dev/null 2>&1 || true
[ "$(wc -l < records/dispatch_audit.jsonl)" -eq 3 ] || fail "audit log did not record the failing provider's attempt"
grep -q '"outcome": "error"' records/dispatch_audit.jsonl || fail "audit log missing error outcome for failing provider"
pass "dispatch -> audit log records every attempt, success and failure alike"

# 15. dispatch --deny-pattern: a matching provider command is rejected
# BEFORE it runs -- proven by a marker file the denied command would have
# created, which must never appear. A mixed batch (one benign, one denied)
# must also fully block, not partially run.
denied_marker="$WORKDIR/denied_marker"
rm -f "$denied_marker"
deny_exit=0
$WKB dispatch --topic "smoke: deny" \
  --provider "danger=touch $denied_marker && echo done" \
  --deny-pattern 'touch ' >/dev/null 2>&1 || deny_exit=$?
[ "$deny_exit" -eq 2 ] || fail "dispatch did not exit 2 on a --deny-pattern match (got $deny_exit)"
[ -e "$denied_marker" ] && fail "denied provider command ran anyway (marker file exists)"

rm -f "$denied_marker"
mixed_exit=0
$WKB dispatch --topic "smoke: deny mixed" \
  --provider "ok=echo fine" \
  --provider "danger=touch $denied_marker" \
  --deny-pattern 'touch ' >/dev/null 2>&1 || mixed_exit=$?
[ "$mixed_exit" -eq 2 ] || fail "mixed batch with a denied provider did not exit 2 (got $mixed_exit)"
[ -e "$denied_marker" ] && fail "denied provider ran even though it was one of several providers"
pass "dispatch --deny-pattern -> rejected provider never runs, blocks whole batch"

echo "ALL SMOKE TESTS PASSED"
