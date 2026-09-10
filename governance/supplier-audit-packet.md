# Supplier audit response: AI in the SDLC

Audience: customer supplier-quality teams, procurement security reviews, and RFP
questionnaires. Owner: QA/RA. Keep to two pages. Review quarterly.

> Most vendors will have no answer to "do you use generative AI in development?"
> within the next year. Having one, with evidence, is a commercial asset. Route
> this through QA/RA and Legal before it leaves the building.

## The standard questions, and where the answer comes from

**Q. Do you use generative AI in your software development lifecycle?**
Yes, as a development tool under documented controls. It does not form part of the
delivered product and does not process customer records. See the tool risk assessment.

**Q. What is the qualification status of the tool?**
Categorised as supporting development software; assurance derives from verification of
output rather than qualification of the generator, consistent with our treatment of
compilers and build tooling. Risk assessment attached, approved by QA/RA, reviewed
annually.

**Q. How do you ensure AI-authored code meets your quality standards?**
Every change carries a committed artifact chain — requirement, specification, plan,
diff, tests, review findings, approval — in version control with author and timestamp.
No source change is possible without an approved plan on disk (enforced by tooling, not
policy). Automated test and lint gates must pass. A human code owner approves; the
agent has no mechanism to approve its own work.

**Q. How is traceability maintained?**
Requirement IDs originate in the specification and flow to test cases and to the
traceability matrix. Sample export available on request.

**Q. What happens if AI-authored code causes a defect in our validated instance?**
Handled under our deviation and CAPA procedure, with customer notification thresholds
defined. See the deviation runbook.

**Q. Could our data or documents be exposed to the AI vendor?**
No. Development environments hold no customer production data. Tool access to
credentials, secrets and network egress is restricted by centrally managed policy that
engineers cannot override.

**Q. What controls exist around changes to the AI configuration?**
The instructions and policies steering the agent are version-controlled, reviewed like
code, and regression-tested by an evaluation suite on every change.

## Evidence pack to hand over

1. This document.
2. The approved tool risk assessment (signatures page).
3. A redacted sample artifact chain for one representative change.
4. A sample traceability export.
5. The controls summary table from the risk assessment.

Do not hand over: session transcripts, source code, or the managed settings file.
