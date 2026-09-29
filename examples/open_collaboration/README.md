# Open collaboration: independent host + external JavaScript client

This is a runnable protocol-conformance example, **not a production service**.
It uses no Wishbud, OPC, wallet, model, remote business system or real payment.
The Python host stores agreements; the Node client supplies all strategy and
computes an actual local artifact. Public fixture credentials represent three
logical roles controlled by one test operator, not three independent owners.

## Run

Requires the repository Python baseline and Node.js 22+. From the repository root:

```sh
python scripts/build_core_distribution.py
# Install the generated wheel from dist/core in a fresh environment, with --no-deps.
python examples/open_collaboration/host.py --db ./collaboration-demo.db --port 8099
```

In another terminal:

```sh
node examples/open_collaboration/client.mjs http://127.0.0.1:8099
```

The client checks the whole sequence:

1. Owner creates goal revision 1; provider and owner accept the frozen agreement.
2. Owner revises intent. The original agreement is **not** silently changed.
3. A new agreement supersedes the original only after both parties consent.
4. External JavaScript computes bytes and their SHA256; the host stores a descriptor.
5. Reviewer checks the exact candidate and frozen terms; a stale-terms review is refused.
6. Recipient records adoption; this does not complete a goal or prove causal impact.
7. Replaying the same commands, including after host restart, returns original receipts.

The fixture host binds only loopback and maps fixed test tokens to authenticated
actors. Payload `actor` fields are rejected. It has no public query endpoint and
never downloads artifact URIs. Do not expose it using a tunnel or proxy.
Production needs real authentication/rotation, visibility and tenant policy,
request/connection quotas, TLS, protected storage and evidence verification.

## Envelope and operations

`POST /commands` with `Authorization: Bearer <test token>`:

```json
{"command_id":"create","operation":"goal.create","payload":{"id":"research-goal","intent":{"title":"Research","description":"Investigate a measured gap","domain":"research","success_criteria":"Observe an agreed result"}}}
```

Actor identity is supplied by the host, never the envelope. A command ID is
unique across the ledger; reusing it with another actor, operation or payload
fails. Do not mint new IDs to recover from ambiguous side effects. This host
has no external side effects; other integrations need original-operation lookup.

| Operation | Required payload fields | Authority / precondition |
|---|---|---|
| `goal.create` | `id`, `intent` (title/description/domain/success_criteria) | Authenticated creator becomes owner |
| `goal.revise` | `goal_id`, `base_revision`, `changes`, `reason`, `evidence_ids` | Owner; current revision CAS; intent-only patch |
| `commitment.propose` | `id`, `goal_id`, `goal_revision`, `provider_id`, `description`, `terms`, `criteria`, `verifier_ids`, `profile_id`; optional `supersedes` | Owner; current goal version; host-installed profile |
| `commitment.accept` | `commitment_id`, `terms_hash` | All required parties consent to exact terms |
| `artifact.submit` | `commitment_id`, `terms_hash`, `artifact` | Active agreement's provider |
| `review.record` | `id`, `artifact_id`, `artifact_sha256`, `terms_hash`, `checks` | Agreed reviewer; all criteria; one immutable review per reviewer/candidate |
| `adoption.record` | `id`, `artifact_id`, `artifact_sha256`, `terms_hash`, `evidence_ids`, `statement` | Recipient; all agreed reviews pass |

An artifact has `id`, `media_type`, `sha256`, `uri`, `size_bytes`, and optionally
the exact schema `usmsb.artifact-reference.v1`. Each check has `criterion_id`,
`status` (`pass` / `fail` / `unknown`), `evidence_ids`, and `reason`. Passing
requires evidence references; references themselves are not verified evidence.

This journal version uses bounded JSON with strings, safe integers, booleans,
null, lists and objects (no floating-point ambiguity); depth ≤16, collections
≤1024, canonical command input ≤128 KiB. The host enforces a persistent command
budget. These are reference-implementation limits, not a scalability claim.

Revision receipts include at most 32 affected commitment IDs, the total count,
and `affected_next_after`. Read subsequent immutable pages with
`revision_impacts(goal_id, revision, after=cursor, limit=32)`; its response has
`commitment_ids` and `next_after`. Large collaborations cannot block revision
merely by making the impact receipt too large.

`get`, `goal_version`, `revision_impacts` and `events` are Python **host-only** query methods. A
deployment must enforce its own visibility rules before exposing them. Updating
principals/profiles in-place by restart is refused; production needs an explicit
policy-migration process (not supplied by this fixture).

Run the automatically checked integration, including host restart:

```sh
python -m pytest tests/portable/test_open_core.py --confcutdir=tests/portable -q
```
