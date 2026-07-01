from codex_doctor.network_probe import parse_curl_metrics
from codex_doctor.schemas import NetworkProbe
from codex_doctor.state_machine import CodexState, diagnose


def test_parse_curl_metrics():
    output = """http_code=401
dns=0.012
connect=0.082
tls=0.231
ttfb=0.620
total=0.621
"""
    data = parse_curl_metrics(output)
    assert data["http_code"] == "401"
    assert data["total"] == "0.621"


def test_http_401_is_reachable_for_diagnosis(events_prompt_old):
    probe = NetworkProbe(target="https://api.openai.com/v1/models", ok=True, http_code=401)
    diagnosis = diagnose(events_prompt_old, probe=probe)
    assert diagnosis.state == CodexState.API_OR_MODEL_WAITING


def test_probe_fail_is_network_suspected(events_prompt_old):
    probe = NetworkProbe(
        target="https://api.openai.com/v1/models",
        ok=False,
        error_type="tls",
        error_message="handshake timeout",
    )
    diagnosis = diagnose(events_prompt_old, probe=probe)
    assert diagnosis.state == CodexState.NETWORK_SUSPECTED
