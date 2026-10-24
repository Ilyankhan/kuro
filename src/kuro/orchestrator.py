import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from kuro.agents.inspector import BinaryInspector
from kuro.agents.probe import DynamicRuntimeProbe
from kuro.agents.synthesizer import CodeSynthesizer
from kuro.agents.verifier import DifferentialParityVerifier
from kuro.config import settings
from kuro.models.schemas import (
    DefectReport,
    InspectionReport,
    ProbeReport,
    SynthesizedProject,
    VerificationReport,
)
from kuro.sandbox.runner import DockerSandboxRunner


class KuroState(TypedDict, total=False):
    binary_path: str
    target_language: str
    workspace_dir: str
    output_dir: Optional[str]
    inspection_report: Optional[InspectionReport]
    probe_report: Optional[ProbeReport]
    candidate_code: Optional[SynthesizedProject]
    verification_report: Optional[VerificationReport]
    defects: Optional[List[DefectReport]]
    retry_count: int
    max_retries: int
    status: str
    current_step: str
    step_message: str
    step_history: List[Dict[str, Any]]
    error: Optional[str]


class KuroOrchestrator:
    """Phase 6: Autonomous LangGraph Cyclic State Machine coordinating

    Inspector -> Probe -> Synthesizer -> Verifier with up to 3 repair cycles.
    """

    def __init__(
        self,
        docker_image: Optional[str] = None,
        max_retries: Optional[int] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        test_count: Optional[int] = None,
    ):
        self.docker_image = docker_image or settings.docker_image
        self.max_retries = max_retries if max_retries is not None else settings.max_repair_cycles
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self.test_count = test_count if test_count is not None else settings.default_test_cases

        self.runner = DockerSandboxRunner(image=self.docker_image)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(KuroState)

        workflow.add_node("inspector", self._inspector_node)
        workflow.add_node("probe", self._probe_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        workflow.add_node("verifier", self._verifier_node)

        workflow.add_edge(START, "inspector")
        workflow.add_edge("inspector", "probe")
        workflow.add_edge("probe", "synthesizer")
        workflow.add_edge("synthesizer", "verifier")

        workflow.add_conditional_edges(
            "verifier",
            self._should_continue,
            {
                "success": END,
                "retry": "synthesizer",
                "max_retries_reached": END,
            },
        )

        return workflow.compile()

    # --- Node Implementations ---

    def _inspector_node(self, state: KuroState) -> Dict[str, Any]:
        """Node 1: Reverse-engineers ELF headers, symbols, and disassembly blocks."""
        bin_path = state["binary_path"]
        inspector = BinaryInspector(bin_path)
        report = inspector.inspect()

        step_info = {
            "node": "inspector",
            "status": "completed",
            "message": f"Identified {report.architecture.value} ELF ({'stripped' if report.is_stripped else 'unstripped'}), "
                       f"{len(report.functions)} domain functions, {len(report.extracted_strings)} strings.",
            "timestamp": time.time(),
        }

        history = list(state.get("step_history", []))
        history.append(step_info)

        return {
            "inspection_report": report,
            "current_step": "inspector",
            "step_message": step_info["message"],
            "step_history": history,
            "status": "inspecting_complete",
        }

    def _probe_node(self, state: KuroState) -> Dict[str, Any]:
        """Node 2: Probes binary behavior and CLI contract inside Docker sandbox."""
        bin_path = state["binary_path"]
        inspection = state["inspection_report"]

        probe_agent = DynamicRuntimeProbe(self.runner)
        probe_report = probe_agent.probe(bin_path, inspection)

        step_info = {
            "node": "probe",
            "status": "completed",
            "message": f"Discovered flags: {probe_report.supported_flags}, "
                       f"subcommands: {probe_report.detected_subcommands}, "
                       f"sample executions: {len(probe_report.sample_runs)}.",
            "timestamp": time.time(),
        }

        history = list(state.get("step_history", []))
        history.append(step_info)

        return {
            "probe_report": probe_report,
            "current_step": "probe",
            "step_message": step_info["message"],
            "step_history": history,
            "status": "probing_complete",
        }

    def _synthesizer_node(self, state: KuroState) -> Dict[str, Any]:
        """Node 3: Generates clean modern multi-file codebase using Gemini Flash."""
        inspection = state["inspection_report"]
        probe_report = state["probe_report"]
        target_lang = state.get("target_language", "python")
        defects = state.get("defects", None)
        retry_count = state.get("retry_count", 0)

        synthesizer = CodeSynthesizer(api_key=self.api_key, model_name=self.model_name)
        project = synthesizer.synthesize(
            inspection=inspection,
            probe=probe_report,
            target_language=target_lang,
            defects=defects,
        )

        # Materialize in workspace directory
        workspace_dir = state.get("workspace_dir")
        if not workspace_dir:
            workspace_dir = tempfile.mkdtemp(prefix="kuro_workspace_")

        target_dir = Path(workspace_dir)
        if target_dir.exists():
            for item in target_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        synthesizer.materialize(project, target_dir)

        msg = f"Synthesized {len(project.files)} modern {target_lang.capitalize()} files (entry: {project.entry_point_file})."
        if defects:
            msg = f"Self-repair cycle {retry_count}: Re-synthesized codebase with defect patches."

        step_info = {
            "node": "synthesizer",
            "status": "completed",
            "message": msg,
            "files": [f.path for f in project.files],
            "retry_count": retry_count,
            "timestamp": time.time(),
        }

        history = list(state.get("step_history", []))
        history.append(step_info)

        return {
            "candidate_code": project,
            "workspace_dir": str(target_dir),
            "current_step": "synthesizer",
            "step_message": msg,
            "step_history": history,
            "status": "synthesizing_complete",
        }

    def _verifier_node(self, state: KuroState) -> Dict[str, Any]:
        """Node 4: Runs differential parity tests between original binary and synthesized code."""
        legacy_binary = state["binary_path"]
        workspace_dir = state["workspace_dir"]
        candidate_code = state["candidate_code"]
        probe_report = state["probe_report"]
        target_lang = state.get("target_language", "python")

        verifier = DifferentialParityVerifier(self.runner)
        report = verifier.verify(
            legacy_binary_path=legacy_binary,
            modern_workspace_dir=workspace_dir,
            modern_entry_file=candidate_code.entry_point_file,
            probe_report=probe_report,
            target_language=target_lang,
            test_count=self.test_count,
        )

        retry_count = state.get("retry_count", 0)
        new_retry = retry_count if report.is_fully_parity_proven else retry_count + 1
        msg = f"Differential parity: {report.parity_percentage}% ({report.passed_tests}/{report.total_tests} passed, {report.failed_tests} defects)."

        step_info = {
            "node": "verifier",
            "status": "completed",
            "parity_percentage": report.parity_percentage,
            "passed_tests": report.passed_tests,
            "failed_tests": report.failed_tests,
            "retry_count": retry_count,
            "message": msg,
            "timestamp": time.time(),
        }

        history = list(state.get("step_history", []))
        history.append(step_info)

        # Update output directory if fully verified or if output_dir requested
        output_dir = state.get("output_dir")
        if output_dir:
            out_path = Path(output_dir)
            CodeSynthesizer.materialize(candidate_code, out_path)

        return {
            "verification_report": report,
            "defects": report.defects if report.defects else None,
            "retry_count": new_retry,
            "current_step": "verifier",
            "step_message": msg,
            "step_history": history,
            "status": "parity_proven" if report.is_fully_parity_proven else "parity_mismatch",
        }

    def _should_continue(self, state: KuroState) -> str:
        """Evaluates whether to terminate or trigger self-repair cycle."""
        ver_report = state.get("verification_report")
        if ver_report and ver_report.is_fully_parity_proven:
            return "success"

        current_retries = state.get("retry_count", 0)
        max_retries = state.get("max_retries", self.max_retries)

        if current_retries < max_retries:
            return "retry"

        return "max_retries_reached"

    # --- Execution Interfaces ---

    def run(
        self,
        binary_path: str,
        target_language: str = "python",
        output_dir: Optional[str] = None,
    ) -> KuroState:
        """Executes the complete modernization pipeline synchronously."""
        initial_state: KuroState = {
            "binary_path": str(Path(binary_path).resolve()),
            "target_language": target_language,
            "output_dir": output_dir,
            "retry_count": 0,
            "max_retries": self.max_retries,
            "status": "started",
            "step_history": [],
        }

        final_state = self.graph.invoke(initial_state)
        return final_state

    def stream_run(
        self,
        binary_path: str,
        target_language: str = "python",
        output_dir: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, KuroState]:
        """Streams state transitions for live telemetry (Streamlit / CLI)."""
        initial_state: KuroState = {
            "binary_path": str(Path(binary_path).resolve()),
            "target_language": target_language,
            "output_dir": output_dir,
            "retry_count": 0,
            "max_retries": self.max_retries,
            "status": "started",
            "step_history": [],
        }

        last_state = initial_state
        for event in self.graph.stream(initial_state, stream_mode="updates"):
            for node_name, updates in event.items():
                last_state = {**last_state, **updates}
                yield {"node": node_name, "state": last_state, "updates": updates}

        return last_state
