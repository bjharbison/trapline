#!/usr/bin/env bash
# Run every browser test. Exit code is non-zero if any test fails.
# Needs: python3 with playwright + chromium (python3 -m playwright install chromium).
set -uo pipefail
cd "$(dirname "$0")"
bash vendor.sh || exit 1
status=0
for t in test_*.py; do
  echo "== $t"
  python3 "$t" || status=1
done
[ $status -eq 0 ] && echo "ALL TESTS PASSED" || echo "SOME TESTS FAILED"
exit $status
