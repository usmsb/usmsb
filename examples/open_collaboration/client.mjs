// External client: Node built-ins only, no SDK / model / Wishbud / OPC.
// Fixture actors are controlled by one test operator, NOT independent people.
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const base = new URL(process.argv[2]);
assert.equal(base.hostname, '127.0.0.1', 'Fixture tokens may only be sent to loopback');
assert.equal(base.protocol, 'http:');
const receipts = [];
async function command(actor, command_id, operation, payload, expected = 200) {
  const response = await fetch(new URL('/commands', base), {
    method: 'POST', headers: { Authorization: `Bearer fixture-${actor}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ command_id, operation, payload }), signal: AbortSignal.timeout(5000),
  });
  const result = await response.json();
  assert.equal(response.status, expected, JSON.stringify(result));
  if (expected === 200) receipts.push(result);
  return result;
}
const intent = { title: 'Produce a reusable measurement', description: 'A local executable produces a verifiable result',
  domain: 'research', success_criteria: 'Agreed computation and explicit recipient adoption' };
const initial = await command('owner', 'create', 'goal.create', { id: 'research-goal', intent });
const criteria = [{ id: 'calculation', description: 'Artifact bytes encode sum(1..10) = 55', evidence_kind: 'artifact' }];
const proposal = { id: 'agreement-v1', goal_id: 'research-goal', goal_revision: 1, provider_id: 'provider',
  description: 'Deliver a JSON result', terms: 'No payment; test fixture; recipient consumes local result',
  criteria, verifier_ids: ['reviewer'], profile_id: 'usmsb:open-collaboration' };
const c1 = (await command('owner', 'propose-v1', 'commitment.propose', proposal)).result;
for (const actor of ['owner', 'provider'])
  await command(actor, `accept-v1-${actor}`, 'commitment.accept', { commitment_id: c1.id, terms_hash: c1.terms_hash });
const revision = (await command('owner', 'revise', 'goal.revise', { goal_id: 'research-goal', base_revision: 1,
  changes: { description: 'Use binary artifact transport with the same agreed calculation' },
  reason: 'Recipient changed transport preference', evidence_ids: ['fixture:recipient-preference'] })).result;
assert.equal(revision.obligations_changed, false);
assert.deepEqual(revision.affected_commitment_ids, ['agreement-v1']);
await command('provider', 'forged-owner', 'goal.revise', { goal_id: 'research-goal', base_revision: 2,
  changes: { title: 'Forged' }, reason: 'invalid', evidence_ids: [] }, 400);
const c2 = (await command('owner', 'amend', 'commitment.propose', {
  ...proposal, id: 'agreement-v2', goal_revision: 2, supersedes: c1.id, description: 'Deliver binary bytes carrying JSON',
})).result;
for (const actor of ['owner', 'provider'])
  await command(actor, `accept-v2-${actor}`, 'commitment.accept', { commitment_id: c2.id, terms_hash: c2.terms_hash });

// Real computation in the external process; the ledger does not run this code.
const bytes = Buffer.from(JSON.stringify({ sum: Array.from({ length: 10 }, (_, i) => i + 1).reduce((a, b) => a + b) }));
const sha256 = createHash('sha256').update(bytes).digest('hex');
const artifact = { id: 'measurement-v2', media_type: 'application/octet-stream', sha256,
  uri: `urn:sha256:${sha256}`, size_bytes: bytes.length };
await command('provider', 'submit', 'artifact.submit', { commitment_id: c2.id, terms_hash: c2.terms_hash, artifact });
await command('reviewer', 'stale-review', 'review.record', { id: 'invalid-review', artifact_id: artifact.id,
  artifact_sha256: sha256, terms_hash: c1.terms_hash, checks: [] }, 400);
// Fixture reviewer actually checks locally available bytes; the core trusts an attributed statement only.
assert.equal(JSON.parse(bytes.toString()).sum, 55);
await command('reviewer', 'review', 'review.record', { id: 'review-v2', artifact_id: artifact.id,
  artifact_sha256: sha256, terms_hash: c2.terms_hash,
  checks: [{ criterion_id: 'calculation', status: 'pass', evidence_ids: [`urn:sha256:${sha256}`],
    reason: 'Fixture verifier parsed the local bytes and checked the expected calculation' }] });
const adoption = (await command('owner', 'adopt', 'adoption.record', { id: 'adoption-v2', artifact_id: artifact.id,
  artifact_sha256: sha256, terms_hash: c2.terms_hash, evidence_ids: ['fixture:local-consumption'],
  statement: `Consumed local measurement ${JSON.parse(bytes.toString()).sum}; no causal or revenue claim` })).result;
assert.equal(adoption.matches_current_goal_revision, true);
assert.equal(adoption.goal_revision, 2);
assert.deepEqual(await command('owner', 'create', 'goal.create', { id: 'research-goal', intent }), initial);
console.log(JSON.stringify({ scenario: 'external-json-client', model_calls: 0, payments: 0,
  claims: 'protocol integration with test identities, not independent customer validation',
  artifact_sha256: sha256, adopted_goal_revision: adoption.goal_revision,
  receipt_sequences: receipts.map(r => r.sequence) }));
