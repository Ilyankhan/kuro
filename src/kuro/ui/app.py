import io
import os
import tempfile
import zipfile
from pathlib import Path
import streamlit as st

from kuro.config import settings
from kuro.orchestrator import KuroOrchestrator

st.set_page_config(
    page_title="Kuro — Binary Modernization Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styles for terminal/cyberpunk aesthetic
st.markdown(
    """
    <style>
    .main-title {
        font-family: 'Courier New', monospace;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .metric-card {
        background-color: #1a1c24;
        border-radius: 8px;
        padding: 12px 18px;
        border: 1px solid #2d3139;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Sidebar settings
with st.sidebar:
    st.title("⚡ Kuro Engine")
    st.caption("Autonomous ELF Binary Reverse Engineering & Modernization")
    st.divider()

    target_lang = st.selectbox(
        "Target Modern Language",
        options=["python", "go"],
        index=0,
        help="Target language for synthesized code repository.",
    )

    max_repair_cycles = st.slider(
        "Max Self-Repair Cycles",
        min_value=0,
        max_value=5,
        value=settings.max_repair_cycles,
        help="Number of times Kuro will patch and re-verify code against failing test vectors.",
    )

    test_vectors_count = st.slider(
        "Verification Test Count",
        min_value=3,
        max_value=25,
        value=5,
        help="Number of randomized and boundary test vectors to run in Docker sandbox.",
    )

    gemini_api_key = st.text_input(
        "Gemini API Key (Optional)",
        value=settings.gemini_api_key,
        type="password",
        help="Leave empty or set to test offline with algorithmic baseline synthesis.",
    )

    st.divider()
    st.markdown("**Core Loop Pipeline:**")
    st.markdown(
        """
    1. 🔍 **Inspector**: ELF headers, symbols & disassembly
    2. 🧪 **Runtime Probe**: CLI flags & stdout discovery
    3. 🧠 **Synthesizer**: Modern typed multi-file code
    4. ⚖️ **Differential Verifier**: 100% parity proof in Docker
    """
    )


# Helper for creating download zip
def create_project_zip(files_list) -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for f in files_list:
            zip_file.writestr(f.path, f.content)
    return zip_buffer.getvalue()


# Main View
st.markdown("<h1 class='main-title'>⚡ Kuro: Binary → Modern Code</h1>", unsafe_allow_html=True)
st.write(
    "Upload a compiled legacy ELF binary (x86_64, C, Go, stripped or unstripped) to extract architecture, "
    "infer runtime behavior, and synthesize an equivalent modernized project."
)

uploaded_file = st.file_uploader(
    "Upload Legacy ELF Binary",
    type=None,
    help="Upload an executable Linux ELF binary (e.g. cipher, calc, CLI utility)",
)

# Demo benchmark pre-selection helper
st.caption("Or test with included benchmarks:")
col_b1, col_b2, _ = st.columns([1, 1, 3])

if "selected_binary_path" not in st.session_state:
    st.session_state.selected_binary_path = None
if "binary_display_name" not in st.session_state:
    st.session_state.binary_display_name = ""
if "is_running" not in st.session_state:
    st.session_state.is_running = False

load_cipher = col_b1.button(
    "📁 Load C Cipher Benchmark",
    disabled=st.session_state.is_running,
)
load_calc = col_b2.button(
    "📁 Load Go Calc Benchmark",
    disabled=st.session_state.is_running,
)

if uploaded_file is not None:
    temp_bin = tempfile.NamedTemporaryFile(delete=False, prefix="kuro_upload_")
    temp_bin.write(uploaded_file.getbuffer())
    temp_bin.close()
    os.chmod(temp_bin.name, 0o755)
    st.session_state.selected_binary_path = temp_bin.name
    st.session_state.binary_display_name = uploaded_file.name
elif load_cipher:
    bench_path = Path(__file__).resolve().parents[3] / "benchmarks" / "c_cipher" / "cipher"
    if bench_path.exists():
        st.session_state.selected_binary_path = str(bench_path)
        st.session_state.binary_display_name = "benchmarks/c_cipher/cipher (C ELF)"
    else:
        st.error(f"Benchmark file not found at {bench_path}")
elif load_calc:
    bench_path = Path(__file__).resolve().parents[3] / "benchmarks" / "go_calc" / "aegis_sample"
    if bench_path.exists():
        st.session_state.selected_binary_path = str(bench_path)
        st.session_state.binary_display_name = "benchmarks/go_calc/aegis_sample (Go ELF)"
    else:
        st.error(f"Benchmark file not found at {bench_path}")

selected_binary_path = st.session_state.selected_binary_path
binary_display_name = st.session_state.binary_display_name

if selected_binary_path:
    st.info(f"Target Binary: `{binary_display_name}`")

    run_disabled = st.session_state.is_running
    if st.button("🚀 Run Autonomous Modernization", type="primary", disabled=run_disabled):
        st.session_state.is_running = True
        orchestrator = KuroOrchestrator(
            api_key=gemini_api_key,
            max_retries=max_repair_cycles,
            test_count=test_vectors_count,
        )

        st.subheader("Live Execution Telemetry")
        status_box = st.status("Initializing Kuro autonomous loop...", expanded=True)

        final_state = None

        with status_box:
            try:
                for event in orchestrator.stream_run(
                    binary_path=selected_binary_path,
                    target_language=target_lang,
                ):
                    node_name = event["node"]
                    state = event["state"]
                    final_state = state

                    if node_name == "inspector":
                        insp = state.get("inspection_report")
                        st.write(
                            f"✅ **[Inspector]** {insp.architecture.value} ELF "
                            f"({'stripped' if insp.is_stripped else 'unstripped'}) | "
                            f"{len(insp.functions)} functions | {len(insp.extracted_strings)} strings"
                        )
                    elif node_name == "probe":
                        probe = state.get("probe_report")
                        st.write(
                            f"✅ **[Runtime Probe]** Discovered flags: `{probe.supported_flags}` | "
                            f"Subcommands: `{probe.detected_subcommands}`"
                        )
                    elif node_name == "synthesizer":
                        synth = state.get("candidate_code")
                        retry = state.get("retry_count", 0)
                        tag = f"Repair Cycle {retry}" if retry > 0 else "Initial Synthesis"
                        st.write(
                            f"✅ **[Synthesizer ({tag})]** Generated {len(synth.files)} files "
                            f"(entry: `{synth.entry_point_file}`)"
                        )
                    elif node_name == "verifier":
                        ver = state.get("verification_report")
                        st.write(
                            f"⚖️ **[Parity Verifier]** Parity: **{ver.parity_percentage}%** "
                            f"({ver.passed_tests}/{ver.total_tests} passed, {ver.failed_tests} defects)"
                        )

                if final_state and final_state.get("status") == "parity_proven":
                    status_box.update(label="✨ Modernization Complete — 100% Parity Proven!", state="complete", expanded=False)
                else:
                    status_box.update(label="Modernization Finished (Inspect parity results below)", state="complete", expanded=False)
            finally:
                st.session_state.is_running = False

        # Results Dashboard
        if final_state:
            st.divider()
            ver_report = final_state.get("verification_report")
            candidate = final_state.get("candidate_code")
            inspection = final_state.get("inspection_report")

            # Top Metrics
            m1, m2, m3, m4 = st.columns(4)
            if ver_report:
                m1.metric("Parity Score", f"{ver_report.parity_percentage}%", delta=f"{ver_report.passed_tests}/{ver_report.total_tests} passed")
                m2.metric("Defects", f"{ver_report.failed_tests}")
            if candidate:
                m3.metric("Synthesized Files", f"{len(candidate.files)}")
            if inspection:
                m4.metric("Architecture", inspection.architecture.value)

            st.divider()

            # Side-by-side Inspection & Code Synthesis
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("🔍 Reverse Engineered Binary")
                tab1, tab2, tab3 = st.tabs(["Disassembly", "Extracted Strings", "Probe CLI"])
                with tab1:
                    if inspection and inspection.functions:
                        selected_func = st.selectbox(
                            "Domain Function",
                            options=[f.name for f in inspection.functions],
                        )
                        for f in inspection.functions:
                            if f.name == selected_func:
                                st.code(f.instructions or "(No disassembly available)", language="nasm")
                    else:
                        st.write("No functions extracted.")
                with tab2:
                    if inspection:
                        st.dataframe(inspection.extracted_strings, columns=["Strings"], use_container_width=True)
                with tab3:
                    probe = final_state.get("probe_report")
                    if probe:
                        st.text(probe.help_text or "No CLI help output captured")

            with col_right:
                st.subheader("✨ Synthesized Modern Repository")
                if candidate and candidate.files:
                    file_options = [f.path for f in candidate.files]
                    chosen_file_path = st.selectbox("View Source File", options=file_options)
                    for f in candidate.files:
                        if f.path == chosen_file_path:
                            lang = "python" if chosen_file_path.endswith(".py") else "go"
                            st.code(f.content, language=lang)

                    # Zip Download
                    zip_data = create_project_zip(candidate.files)
                    st.download_button(
                        label="⬇️ Download Modernized Project (.zip)",
                        data=zip_data,
                        file_name="kuro_modernized_project.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True,
                    )
                else:
                    st.warning("No candidate code generated.")

            # Defect inspection if any
            if ver_report and ver_report.defects:
                st.divider()
                st.subheader("⚠️ Parity Defect Log")
                for d in ver_report.defects:
                    with st.expander(f"Defect on args: {d.command_args}"):
                        st.write(f"**Diagnostic**: {d.diagnostic_hint}")
                        st.write(f"**Expected stdout**: `{d.expected_stdout}`")
                        st.write(f"**Actual stdout**: `{d.actual_stdout}`")
