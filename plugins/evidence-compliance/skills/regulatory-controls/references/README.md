# Control set references

One file per framework. The `regulatory-controls` skill loads only the sets named in
`.evidence/context/compliance.md`, so the size of this directory costs nothing at
runtime.

## What ships here

These are **starting points drafted from public sources, not authoritative
interpretations.** They are structured to be useful to an agent reviewing a diff, which
is a different job from satisfying an auditor. Have your compliance owner review any set
before you rely on it, and expect to edit it.

| File | Framework | Typical industry |
| --- | --- | --- |
| `21-cfr-part-11.md` | FDA electronic records and signatures | Life sciences, regulated manufacturing |
| `eu-gmp-annex-11.md` | EU computerised systems in GMP | Life sciences (EU) |
| `iec-62304.md` | Medical device software lifecycle | Medical devices |
| `iso-13485.md` | Medical device quality management | Medical devices |
| `soc2.md` | Trust services criteria | SaaS, B2B software |
| `hipaa.md` | US protected health information | Healthcare, health tech |
| `pci-dss.md` | Payment card data | Anything handling card data |
| `gdpr.md` | EU personal data protection | Anything with EU personal data |
| `iso-27001.md` | ISO/IEC 27001:2022 Annex A (development and change controls) | Any organisation holding or pursuing ISO 27001 certification |
| `nist-ssdf.md` | NIST SP 800-218 v1.1 Secure Software Development Framework | Software sold to US federal agencies; secure-development attestation |

Every shipped set carries `Owner: UNASSIGNED` until the adopting organisation names an
owner. `evidence doctor` warns while that token is present, and the `regulatory-controls`
skill surfaces it to the human whenever the set is used. Replace it with a named owner
and a real review date once your compliance owner has reviewed the set.

## Writing your own

Most organisations need one. Follow the same shape:

```markdown
# <Framework name>
> Scope, and what it does not cover. Source of this interpretation.
> Owner: <named person> (or `Owner: UNASSIGNED` until one is named). Last reviewed: <date>.

## Controls
| ID | Control | What to check in a change | Typical evidence |
| --- | --- | --- | --- |
| <FW-01> | <requirement in plain language> | <what a reviewer looks for in a diff> | <file, test, audit event, config> |

## Blocking classes
<Which findings must block a merge rather than inform the reviewer.>

## Common misses
<The controls that get forgotten in this framework specifically. This section is the
one that earns its keep — fill it from your own review findings over time.>
```

Two rules that make the difference between a useful set and a checklist nobody reads:

- **Write "what to check in a change", not the regulation text.** A reviewer needs to
  know what to look for in a diff. Quoting the statute helps nobody.
- **Give every control a stable ID.** They get cited in findings, evidence packages and
  traceability rows.
