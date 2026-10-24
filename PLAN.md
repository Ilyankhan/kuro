# Kuro: Detailed Implementation Plan & Phased Roadmap

## Overview
This roadmap decomposes **Kuro** (Autonomous Binary Modernization Swarm) into discrete, testable phases. In accordance with requirements, this plan focuses entirely on the core engine, low-level binary tooling, multi-agent LangGraph orchestration, Docker sandboxing, and differential verification. - **Frontend UI:** Streamlit pure Python dashboard (live agent step visualization, side-by-side assembly/code diff, file uploader, and zip export).

---

## Phase 1: Environment & Sandboxing Foundations
**Goal:** Establish the isolated execution environment, dependency management, and deterministic test subject binaries.

### Tasks:
1. **Python Project Setup:**
   - Define `pyproject.toml` / `requirements.txt` with:
     - `langgraph` & `langchain-core`
     - `google-genai` (official Google Gemini SDK)
     - `r2pipe` (Radare2 Python bridge)
     - `docker` (Docker Python SDK)
     - `pydantic` v2 (strict type schemas)
     - `rich` & `typer` (CLI execution & terminal telemetry)
     - `pytest`
2. **Docker Sandbox Image (`kuro-sandbox`):**
   - Create Dockerfile based on `debian:bookworm-slim`.
   - Install essential runtimes: Python 3.11, Go 1.22+, `gcc`, `glibc`, `binutils`.
   - Configure non-root execution user (`kuro-runner`) with CPU/memory caps and dropped network capabilities (`--network none`).
3. **Benchmark Test Binaries:**
   - Create and compile **Binary A (C CLI Utility)**: An algorithmic CLI tool with flags, arguments, and exit codes (e.g., custom hashing/encoding tool).
   - Create and compile **Binary B (Go CLI Utility)**: A Go CLI utility mimicking `aegis` patterns (subcommands, custom structs, flag parsing) to test Go symbol extraction and runtime filtering.

---

## Phase 2: Agent 1 — Binary Inspector & Symbol Extractor
**Goal:** Ingest raw ELF binaries, extract architectural metadata, function control flow graphs (CFGs), and filter Go runtime bloat.

### Tasks:
1. **Architecture & Header Parser:**
   - Validate ELF format, endianness, bitness (x86_64, ARM64), and strip status using `readelf` / `r2pipe`.
2. **Go Symbol Demangler & Runtime Filter:**
   - Parse `.gopclntab` to extract function names, types, and source paths.
   - Implement filtering pipeline to eliminate `runtime.*`, `internal/*`, and standard library functions (`fmt.*`, `os.*`), isolating only user-defined packages (e.g. `main.*`).
3. **Control Flow Graph & Disassembly Extraction:**
   - Use `radare2` to disassemble user functions, identify basic blocks, branch conditions, and string references.
4. **Data Schema (`InspectionReport`):**
   - Output typed Pydantic model with functions list, strings, entry point, and Go package structure.

---

## Phase 3: Agent 2 — Dynamic Runtime Probe
**Goal:** Probe the binary inside the Docker sandbox to infer CLI contracts, argument expectations, and exit behavior.

### Tasks:
1. **Docker Subprocess Runner:**
   - Implement `DockerProbeRunner` that runs commands in ephemeral sandbox containers with strict timeout enforcement (5 seconds max per run).
2. **Heuristic CLI Fuzzing:**
   - Probe binary with permutations: `--help`, `-h`, `-v`, empty invocation, random string flags, non-existent files.
   - Capture `stdout`, `stderr`, and exit code (`0`, `1`, `127`, etc.).
3. **Contract Inference:**
   - Infer required vs optional flags, argument types (string, integer, file path), and error response formats.
4. **Data Schema (`ProbeReport`):**
   - Output structured CLI invocation contract.

---

## Phase 4: Agent 3 — Modern Code Synthesizer
**Goal:** Translate low-level analysis into clean, idiomatic, multi-file modern Python and Go repositories.

### Tasks:
1. **Gemini 2.5 Flash SDK Integration:**
   - Configure official `google-genai` client with structured output schema support.
2. **Prompt Architecture:**
   - System prompt encoding senior software engineering principles (clean architecture, strong typing, separation of concerns, docstrings).
   - Input: `InspectionReport` + `ProbeReport` + target language (`python` or `go`).
3. **Multi-File Structured Generation:**
   - LLM generates a JSON structure mapping file paths (`src/core.py`, `src/cli.py`, `main.py`) to file contents and dependency order.
4. **Codebase Materializer:**
   - Write files to an isolated directory on disk, ensuring correct imports and package definitions.

---

## Phase 5: Agent 4 — Differential Parity Verifier & Feedback Loop
**Goal:** Empirically prove behavioral identity between the legacy binary and modern code, fixing defects automatically.

### Tasks:
1. **Test Vector Generator:**
   - Generate 50–100 edge-case input vectors based on the `ProbeReport` (valid flags, invalid flags, empty inputs, edge numeric values, special characters).
2. **Dual Sandbox Execution Harness:**
   - In parallel inside Docker:
     - Run `Old Binary [args]` ➔ capture `(stdout_1, stderr_1, code_1)`
     - Run `New Code [args]` (e.g., `python3 main.py [args]` or `go run . [args]`) ➔ capture `(stdout_2, stderr_2, code_2)`
3. **Parity Evaluation:**
   - Compare output byte-for-byte and verify matching exit codes.
4. **Defect Report & Self-Repair Bridge:**
   - If mismatches occur: format exact failing input, expected output, and actual output into a `DefectReport`.
   - Pass `DefectReport` back to Agent 3 (Synthesizer) for iterative code patching.

---

## Phase 6: LangGraph Cyclic Orchestration Engine
**Goal:** Unify the 4 agents into an autonomous, stateful, self-healing graph.

### Tasks:
1. **State Definition (`KuroState`):**
   - Store: `binary_path`, `target_lang`, `inspection_report`, `probe_report`, `candidate_code`, `test_results`, `retry_count` (max 3), `status`.
2. **Graph Topology & Routing:**
   - `START` ➔ `inspector_node` ➔ `probe_node` ➔ `synthesizer_node` ➔ `verifier_node`
   - Conditional Edge on `verifier_node`:
     - If `100% parity` ➔ `END` (Success)
     - If `parity < 100%` and `retry_count < 3` ➔ increment `retry_count` ➔ `synthesizer_node` (Self-Repair)
     - If `retry_count >= 3` ➔ `END` (Partial parity checkpoint with diagnostic report)
3. **CLI Runner with Rich Terminal Telemetry:**
   - Implement `kuro decompile <binary_path> --target go|python` with animated agent activity cards, live diffs, and parity score tables.

---

## Phase 7: End-to-End Benchmark & Aegis CLI Test
**Goal:** Verify full pipeline on real binaries.

### Tasks:
1. **Validate on C Benchmark:** Verify 100% parity on compiled C utility.
2. **Validate on Go Aegis CLI:** Test stripping of Go runtime and reconstruction of `aegis` CLI package.
3. **Metrics & Tracing Report:** Log token usage, turnaround time, and parity pass rates.
