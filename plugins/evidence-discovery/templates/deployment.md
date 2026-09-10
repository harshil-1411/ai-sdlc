# Repository profile — deployment stack

## Infrastructure as code
- [confirmed] tool: <CDK / Terraform / CloudFormation / SAM / Helm / other>, location `<path>`
- [confirmed] state/backend: <where>

## Runtime services
| Service | Purpose | Defined in | Confidence |
| --- | --- | --- | --- |

## Environments
| Environment | Account/Project | Region(s) | Who can deploy | Agent autonomy tier |
| --- | --- | --- | --- | --- |
| dev | | | | agent may deploy |
| staging/UAT | | | | agent prepares, human authorises |
| validation | | | | human only |
| production | | | | human only — release authorisation required |

## Data residency
- [confirmed] regions in use and what determines placement
- [confirmed] which data may not cross which boundary

## Pipelines
- [confirmed] CI system: <what>, config `<file>`
- [confirmed] stages: <list>
- [confirmed] deployment mechanism per environment

## Rollback
- [confirmed] rollback command / mechanism per environment
- [confirmed] last rehearsed: <date> — if never, mark [ASK]

## Open questions — [ASK]
