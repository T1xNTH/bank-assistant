"""decide_route: PII, confidential chunks or force_local -> local-chat; otherwise cloud-chat (CI)."""

import pytest

from app.routing import CLOUD_ALIAS, LOCAL_ALIAS, decide_route


@pytest.mark.parametrize("pii", [["CCCD"], ["ACCOUNT_NUMBER"], ["PHONE_NUMBER"], ["PHONE_NUMBER", "CCCD"]])
def test_pii_in_question_routes_local(pii):
    decision = decide_route(pii, ["public"])
    assert (decision.route, decision.alias) == ("local", "local-chat")
    assert "pii" in decision.reason


CONFIDENTIAL = [["confidential"], ["public", "confidential"], ["internal", "confidential"]]


@pytest.mark.parametrize("classifications", CONFIDENTIAL)
def test_any_confidential_chunk_routes_local(classifications):
    decision = decide_route([], classifications)
    assert (decision.route, decision.alias) == ("local", "local-chat")
    assert "confidential" in decision.reason


@pytest.mark.parametrize("classifications", [[], ["public"], ["internal"], ["public", "internal", "public"]])
def test_no_pii_and_public_or_internal_chunks_route_cloud(classifications):
    decision = decide_route([], classifications)
    assert (decision.route, decision.alias) == ("cloud", "cloud-chat")


@pytest.mark.parametrize("pii,classifications", [([], []), ([], ["public"]), (["CCCD"], ["confidential"])])
def test_force_local_always_routes_local(pii, classifications):
    decision = decide_route(pii, classifications, force_local=True)
    assert (decision.route, decision.alias) == ("local", "local-chat")
    assert "force_local" in decision.reason


@pytest.mark.parametrize("label", ["secret", "Confidential", "", "restricted"])
def test_unknown_classification_fails_closed_to_local(label):
    assert decide_route([], ["public", label]).route == "local"


def test_aliases_match_the_gateway_config():
    assert (LOCAL_ALIAS, CLOUD_ALIAS) == ("local-chat", "cloud-chat")
