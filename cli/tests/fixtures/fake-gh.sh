#!/bin/bash
# Stand-in for the GitHub CLI, selected with EVIDENCE_GH=<this file>.
# Records every call in $FAKE_GH_LOG and answers with canned JSON.
[ -n "${FAKE_GH_LOG:-}" ] && echo "$*" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "issue view")
    if [ "$3" = "42" ]; then
      echo '{"number":42,"title":"Demo issue","state":"OPEN","url":"https://github.com/o/r/issues/42"}'
    else
      echo "GraphQL: Could not resolve to an issue with the number of $3." >&2
      exit 1
    fi ;;
  "issue comment")
    echo "https://github.com/o/r/issues/$3#issuecomment-1" ;;
  "pr list")
    echo '[{"number":7,"title":"FIX-1: implement the demo","reviews":[{"author":{"login":"alice"},"state":"APPROVED"},{"author":{"login":"bob"},"state":"COMMENTED"}]},{"number":8,"title":"unrelated","reviews":[{"author":{"login":"mallory"},"state":"APPROVED"}]}]' ;;
  *) echo "fake gh: unsupported: $*" >&2; exit 2 ;;
esac
