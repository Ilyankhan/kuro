from pathlib import Path
from kuro.orchestrator import KuroOrchestrator


def test_orchestrator_initialization():
    orch = KuroOrchestrator(max_retries=2)
    assert orch.max_retries == 2
    assert orch.graph is not None


def test_orchestrator_end_to_end_c_cipher():
    bin_path = "/home/ilyan/random/kuro/benchmarks/c_cipher/cipher"
    orch = KuroOrchestrator(api_key="", max_retries=1, test_count=3)

    final_state = orch.run(binary_path=bin_path, target_language="python")

    assert final_state["status"] in ("parity_proven", "parity_mismatch")
    assert final_state["inspection_report"] is not None
    assert final_state["probe_report"] is not None
    assert final_state["candidate_code"] is not None
    assert final_state["verification_report"] is not None
    assert len(final_state["step_history"]) >= 4

    # Parity should be 100% on C benchmark with baseline synthesizer
    assert final_state["verification_report"].parity_percentage == 100.0


def test_orchestrator_streaming():
    bin_path = "/home/ilyan/random/kuro/benchmarks/go_calc/aegis_sample"
    orch = KuroOrchestrator(api_key="", max_retries=1, test_count=3)

    events = []
    for event in orch.stream_run(binary_path=bin_path, target_language="python"):
        events.append(event["node"])

    assert "inspector" in events
    assert "probe" in events
    assert "synthesizer" in events
    assert "verifier" in events
