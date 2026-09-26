import pytest
from usmsb_sdk.growth_economic_harness.ports import enforce_cognitive_request_policy

AUTH = {'allowed': True, 'classifications': ['tenant_authorized'], 'destinations': ['opc_conductor', 'llm', 'agent'],
        'authorization_ref': 'growth-program://fixture', 'pii_field_count': 0, 'contains_customer_transcript': False,
        'contains_payment_data': False, 'contains_logistics_data': False, 'contains_credentials': False}
# This actual fixture-generated digest caused a nondeterministic Host failure.
DIGEST = 'sha256:8213933132f107b4e3e5c974c9b2ba19366335428ac6fced2716e81be53ceb1f'


def test_opaque_canonical_digest_does_not_randomly_become_phone_pii():
    enforce_cognitive_request_policy(AUTH, {'metadata': {'tenant_gateway_attestation': {'observation_artifact_sha256': DIGEST}}})


@pytest.mark.parametrize('text', ['13800138000', DIGEST + ' 13800138000', '手机号 ' + DIGEST,
                                  DIGEST[7:], DIGEST + 'f', 'user@example.com', 'api_key=secret-fixture'])
def test_real_sensitive_text_and_noncanonical_digest_are_still_rejected(text):
    with pytest.raises(ValueError, match='sensitive-data'):
        enforce_cognitive_request_policy(AUTH, {'body': text})


@pytest.mark.parametrize('key', ['phone', 'email', 'customer_id', 'password'])
def test_digest_cannot_disguise_forbidden_field(key):
    with pytest.raises(ValueError, match='forbidden sensitive field'):
        enforce_cognitive_request_policy(AUTH, {key: DIGEST})


def test_digest_does_not_bypass_host_authorization():
    with pytest.raises(ValueError, match='authorized data boundary'):
        enforce_cognitive_request_policy({}, {'hash': DIGEST})
