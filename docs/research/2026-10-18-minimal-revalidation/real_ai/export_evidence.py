"""Export only reviewed synthetic experiment evidence, never auth or databases.

This is an evidence exporter, not an evaluator. It preserves the original model
decision/artifact and declared failures; it does not assign a semantic pass.
Outputs are generated artifacts. Local source paths are not published.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

RUNS = ('goal-v1', 'goal-v2', 'missing-v1', 'partner-v1')
RECEIPT_FIELDS = ('provider', 'external_run_id', 'input_tokens', 'output_tokens', 'host_exit_code')
TURN_FIELDS = ('id', 'run_id', 'protocol', 'understanding', 'decision', 'next_action',
               'outlook', 'learning', 'basis_refs', 'uncertainties', 'provenance',
               'verification', 'goal_revision', 'experience_basis', 'late_result')
ARTIFACT_FIELDS = ('id', 'run_id', 'title', 'format', 'content', 'verification', 'origin')
CHILD_FIELDS = ('id', 'status', 'capability_id', 'capability_arguments', 'artifact_id',
                'cost_minor', 'cost_status', 'currency', 'charged_by_wishbud')
REPORT_FIELDS = ('case', 'evidence_kind', 'parent_status', 'child_count', 'child_statuses',
                 'probe_cost_units', 'errors', 'business_effect', 'semantic_behavior_pass',
                 'independent_participants', 'production_changes', 'loopback_stopped',
                 'all_children_stopped')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def pick(value, fields):
    return {key: value[key] for key in fields if key in value}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_run(folder):
    report, detail = read(folder/'report.json'), read(folder/'detail.json')
    actions = list((folder/'coordinator').rglob('action.json'))
    if len(actions) != 1:
        raise ValueError('Exactly one original model action required, including failed runs')
    action = read(actions[0])
    # Keep the original action string, not a rewritten interpretation.
    if set(action) - {'action', 'cause_event_ids', 'data_json', 'reason'}:
        raise ValueError('Unexpected action surface; review before publication')
    payload = json.loads(action['data_json'])
    if set(payload) - {'summary', 'agent_turn', 'artifact'}:
        raise ValueError('Unexpected candidate fields; review before publication')
    originals = sorted((folder/'reader').rglob('fixture-original.json'))
    return {
        'schema': 'usmsb.synthetic-real-ai-evidence.v1',
        'experiment': folder.name.removeprefix('revalidation-20261018-live-'),
        'protocol': read(folder/'protocol.json'),
        'report': {**pick(report, REPORT_FIELDS),
                   'parent_receipt': pick(report.get('parent_receipt') or {}, RECEIPT_FIELDS)},
        'goal': pick(detail['pursuit'], ('id', 'intention', 'criterion', 'constraints', 'revision')),
        'original_model_action': action,
        'saved_turns': [pick(t, TURN_FIELDS) for t in detail['agent_turns']],
        'artifacts': [pick(a, ARTIFACT_FIELDS) for a in detail['artifacts']],
        'children': [{**pick(c, CHILD_FIELDS), 'receipt': pick(c.get('receipt') or {}, RECEIPT_FIELDS)}
                     for c in detail['delegations']],
        'original_reads': [read(p) for p in originals],
        'source_sha256': {'report.json': digest(folder/'report.json'),
                          'detail.json': digest(folder/'detail.json'),
                          'action.json': digest(actions[0])},
        'boundary': 'Real CLI inference; synthetic history and tools; no business effect; '
                    'selected evidence export, not full audit archive or independent attestation',
    }


def safe_bytes(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n'
    # Fail closed: never silently redact a potentially meaningful model result.
    # This is a guard, not a claim of universal secret detection.
    if re.search(r'(?i)(bearer\s+[a-z0-9_.-]+|sk-[a-z0-9_-]{16,}|[a-z]:[\\/]|'
                 r'"(?:token|lease|access_token|refresh_token|api_key|password)"\s*:)', encoded):
        raise ValueError('Potential credential/private-path surface: manual review required')
    return encoded.encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    expected = {run+'.json': safe_bytes(export_run(args.source_root/('revalidation-20261018-live-'+run)))
                for run in RUNS}
    if args.check:
        if {p.name for p in args.output.iterdir()} != set(expected):
            raise ValueError('Missing or extra exported files')
        if any((args.output/name).read_bytes() != content for name, content in expected.items()):
            raise ValueError('Export differs from original experiment')
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, content in expected.items():
            (args.output/name).write_bytes(content)
    print(json.dumps({'checked' if args.check else 'exported': len(expected),
                      'model_invocations': 0, 'semantic_evaluation': 'manual_review_required'}))


if __name__ == '__main__':
    main()
