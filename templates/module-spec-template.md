# Module specification: [module name]

## Control information

| Field | Value |
|---|---|
| Module ID | Mxx |
| Owner | [name/role] |
| Version | 0.1 |
| Maturity | Concept / Proof / Alpha / EVT / DVT / PVT / Released |
| Last reviewed | YYYY-MM-DD |
| Adjacent modules | [IDs/names] |

## Purpose

[One paragraph describing the single responsibility and customer/program reason this module exists.]

## Explicit non-responsibilities

- [What this module must not decide or implement]
- [Boundary that belongs to another module]

## Inputs

| Input | Source | Contract/version | Freshness/quality requirement | Failure behavior |
|---|---|---|---|---|
| [name] | [module/source] | [version] | [requirement] | [behavior] |

## Outputs

| Output | Consumer | Contract/version | Guarantees | Expiry/failure behavior |
|---|---|---|---|---|
| [name] | [module] | [version] | [guarantees] | [behavior] |

## Behavior

### Normal flow

1. [Step]
2. [Step]

### Local state/system-override rules

[Rules owned by this module only. Application packs do not arbitrate against other packs; exactly one activation may publish output.]

### Application-pack lifecycle, when applicable

| Field | Definition |
|---|---|
| Stable pack ID/version | [ID and version] |
| Compatible host API | [range] |
| Permissions | [declared application/OS permissions] |
| Start/stop behavior | [deterministic lifecycle] |
| Activation-generation handling | [how late output is prevented/rejected] |
| Visual recipe ownership | [pack-owned recipe and shared limits] |
| Device access | None; use host interfaces only |

### Configuration and defaults

| Setting | Default | Valid range/options | User-visible? | Reason |
|---|---|---|---|---|
| [setting] | [default] | [range] | Yes/No | [reason] |

## Failure and stale-data behavior

| Failure | Detection | Safe response | Diagnostic evidence | Recovery |
|---|---|---|---|---|
| [failure] | [method] | [response] | [evidence] | [path] |

## Privacy and security

- Data received/created/stored
- Required permissions/privileges
- Trust boundaries
- Sensitive fields and redaction
- Update/dependency considerations
- Abuse/malformed-input behavior

## Performance/resource budget

| Metric | Target | Maximum | Measurement method |
|---|---:|---:|---|
| CPU | [target] | [max] | [method] |
| Memory | [target] | [max] | [method] |
| Latency | [target] | [max] | [method] |

## Diagnostics and observability

- Health/status fields
- User-facing explanation
- Privacy-safe logs/events
- Support export contents
- Factory/engineering-only diagnostics

## Dependencies

| Dependency | Version/maturity needed | Owner | Risk if unavailable |
|---|---|---|---|
| [dependency] | [need] | [owner] | [risk] |

## Acceptance tests

| ID | Scenario | Expected evidence | Stage required |
|---|---|---|---|
| MOD-001 | [scenario] | [evidence] | Alpha/EVT/etc. |

## Rollback/replacement plan

[How this module can be disabled, reverted, or replaced without destabilizing the whole product.]

## Open risks and decisions

| ID | Item | Owner | Due/gate | Link |
|---|---|---|---|---|
| [ID] | [risk/decision] | [owner] | [gate] | [record] |

## Definition of done

- [ ] Inputs/outputs and contract version approved
- [ ] Unsupported/failure/stale behavior tested
- [ ] Privacy/security review complete
- [ ] Resource budget measured
- [ ] Diagnostics and explanation complete
- [ ] Acceptance evidence linked
- [ ] Dependencies handed off
- [ ] Rollback/replacement demonstrated
- [ ] If this is a pack, atomic activation/deactivation and late-event rejection demonstrated
- [ ] If this is a pack, compatible update works without direct device access or firmware change
- [ ] Risks/decisions updated
