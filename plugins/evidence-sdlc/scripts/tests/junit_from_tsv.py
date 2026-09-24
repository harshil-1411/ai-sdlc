#!/usr/bin/env python3
"""junit_from_tsv.py <suite> <out.xml>: read "pass|fail<TAB>label" lines on stdin, write JUnit XML."""
import sys
from xml.sax.saxutils import quoteattr

suite, out = sys.argv[1], sys.argv[2]
rows = [l.rstrip("\n").split("\t", 1) for l in sys.stdin if "\t" in l]
fails = sum(1 for s, _ in rows if s == "fail")
lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         f"<testsuite name={quoteattr(suite)} tests=\"{len(rows)}\" failures=\"{fails}\">"]
for status, label in rows:
    body = '<failure message="failed"/>' if status == "fail" else ""
    lines.append(f"  <testcase classname={quoteattr(suite)} name={quoteattr(label)}>{body}</testcase>")
lines.append("</testsuite>")
open(out, "w").write("\n".join(lines) + "\n")
