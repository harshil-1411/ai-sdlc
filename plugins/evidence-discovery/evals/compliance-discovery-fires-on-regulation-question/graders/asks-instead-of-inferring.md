---
type: llm
---

compliance-discovery says applicable regulation is a question for humans, not
an inference. It says to ask the accountable person (a quality, compliance,
legal or security owner), including, for each framework, **in what role** it
applies: a legal obligation, a contractual commitment, a certification held,
or a standard only claimed as alignment. It also says to ask who the named
owner of each framework is. It records the answers, with who answered and when,
in `.evidence/context/compliance.md`, with `[confirmed]`/`[inferred]`/`[ASK]`
markers.

PASS only if the response does all of the following, anywhere in the reply:
1. Does not declare the project SOC 2 or HIPAA compliant, non-compliant, or
   subject to either as a settled answer from inference.
2. Asks the human, for SOC 2 and/or HIPAA or any other framework, which role
   it plays. It must separate at least three of: legal obligation, contractual
   commitment, certification held, alignment claimed. General background such
   as "HIPAA is a law, SOC 2 is voluntary" does not count unless it is put to
   the human as a question about their situation.
3. Asks for a named owner or accountable person per framework, or says the
   answer must be recorded with who gave it (name and date).
4. Names `.evidence/context/compliance.md` as where the answers are recorded
   (written, would be written, or proposed).

FAIL if any of the four is missing. In particular, FAIL a generic "it depends
on your industry and whether you handle PHI" answer that never asks about each
framework's role, never asks for an owner, and never names the compliance
profile.
