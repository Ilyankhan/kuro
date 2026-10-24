# Product Requirements Document (PRD)
## Project Code Name: **Kuro** (Autonomous Binary Modernization Swarm)

---

## 1. Executive Summary
**Kuro** is an enterprise-grade multi-agent autonomous system designed to decompile, reverse-engineer, and modernize legacy stripped closed-source CLI binaries (C/C++ and Go Linux ELF executables) into clean, idiomatic, and maintainable **Python** and **Go** codebases. 

Unlike traditional decompilers (Ghidra, IDA Pro) that output unintelligible assembly or obfuscated C pseudocode with no semantic context, Kuro orchestrates a cyclical multi-agent graph (via **LangGraph**) to probe binary behavior, reconstruct domain logic, partition multi-file architectures, and mathematically prove 100% I/O parity through automated differential sandbox testing inside isolated **Docker** containers.

---

## 2. Key Problem & Value Proposition
- **Legacy Traps:** Thousands of organizations run mission-critical 10-to-20-year-old compiled binaries where the original source code is lost, dependencies are deprecated, and the original developers are gone.
- **Manual Nightmare:** Human reverse engineering of stripped binaries costs tens of thousands of dollars and months of manual assembly inspection.
- **The Kuro Solution:** Fully autonomous, zero-human-labor recovery of working, modern code with empirical proof of identical execution behavior in minutes.

---

## 3. System Architecture & Topology

```
                  ┌───────────────────────────────┐
                  │       Web Dashboard (UI)      │
                  │   (Vite + React + Tailwind)   │
                  └───────────────┬───────────────┘
                                  │ Upload Binary & Options
                                  ▼
                     FastAPI Orchestrator Backend
                                  │
    ┌─────────────────────────────┴─────────────────────────────┐
    │                 LangGraph Multi-Agent Cycle                │
    │                                                           │
    │  [1. Inspector Agent] ──▶ Extracts symbols, CFGs, strings │
    │         │                 (r2pipe, objdump, Go p机lntab)    │
    │         ▼                                                 │
    │  [2. Dynamic Probe]   ──▶ Runs dummy I/O in Docker        │
    │         │                 (captures stdout/err/exit codes)│
    │         ▼                                                 │
    │  [3. Synthesizer]     ──▶ Generates clean Go/Python files │
    │         │                 (structured JSON multi-file)    │
    │         ▼                                                 │
    │  [4. Verifier Agent]  ──▶ Runs 50-100 edge case inputs    │
    │         │                 against OLD binary vs NEW code  │
    │         │                                                 │
    │         ├───(Mismatch detected: max 3 cycles)─────────────┘
    │         │    (Feedback diff routed back to Synthesizer)
    │         ▼
    │     [Parity Gate] (Success: 100% I/O match)
    └─────────┬─────────────────────────────────────────────────┘
              │
              ▼
   [Download Modern Repo / Live Side-by-Side Diff]
```

---

## 4. Agent Specifications

### Agent 1: Inspector & Symbol Extractor
- **Role:** Static binary analysis and structural triage.
- **Tools:** `radare2` (`r2pipe`), `objdump`, `nm`, `readelf`.
- **Go Specialization:** Inspects `.gopclntab` to extract real function names and package paths; automatically filters out internal `runtime.*` and standard library clutter to isolate user code.
- **Output:** Structured JSON schema describing function boundaries, call graphs, strings, CLI flag hints, and entry points.

### Agent 2: Dynamic Runtime Probe
- **Role:** Empirical black-box behavioral profiling.
- **Tools:** Isolated Docker container runner with subprocess timeouts and security limits.
- **Action:** Executes the binary with exploratory flags (`-h`, `--help`, `-v`, empty arguments, sample strings).
- **Output:** CLI signature specification (required arguments, flags, expected stdin, exit codes, and output patterns).

### Agent 3: Modern Code Synthesizer
- **Role:** Architecture partitioning and idiomatic code generation.
- **Engine:** Google Gemini 2.5 Flash (1M+ token context window via official SDK).
- **Behavior:** 
  - Groups related functions into logical domains (e.g., `cli.py`, `core.py`, `utils.py`).
  - Emits a structured multi-file JSON payload.
  - Implements type hints, docstrings, idiomatic error handling, and standard library conventions.

### Agent 4: Differential Parity Verifier
- **Role:** Empirical test generation and behavioral validation.
- **Tools:** Docker execution engine, fuzzing generator.
- **Action:**
  - Generates 50–100 edge-case test vectors (empty strings, large integers, negative inputs, unusual flags).
  - Executes test vector side-by-side: `Old Binary` vs `New Generated Code`.
  - Compares stdout, stderr, and exit codes byte-for-byte.
- **Feedback Loop:** If any test fails, extracts the minimal failing reproduction case and routes it back to the **Synthesizer Agent** for targeted auto-repair (up to 3 automated cycles).

---

## 5. User Journey & UI/UX Requirements

1. **Dashboard Home:**
   - Drag-and-drop zone for Linux ELF binary files (x86_64 / ARM64).
   - Target language selector: **Python** or **Go**.
   - Optional test harness config (number of parity test cases: 25, 50, 100).
2. **Live Swarm Terminal & Agent Visualizer:**
   - Real-time Server-Sent Events (SSE) streaming of agent thought processes, commands executed, and graph transitions.
   - Live visual step cards: `Inspecting` ➔ `Probing` ➔ `Synthesizing` ➔ `Verifying (Pass 48/50)`.
3. **Parity & Diff Reviewer:**
   - Side-by-side split view: Disassembled Assembly/Symbols vs. Modern Generated Code.
   - Parity audit table showing exact test vectors passed/failed.
   - One-click **"Download Verified Source Code (.zip)"**.

---

## 6. Non-Functional Requirements & Guardrails

- **Zero-Cost Operation:** 100% runnable on free-tier services (Google Gemini Flash free tier + local Docker daemon).
- **Sandboxing & Safety:** Untrusted binaries and synthesized code are strictly executed inside non-root Docker containers with CPU/memory limits (`--memory="512m" --cpus="1.0" --network none`).
- **Resilience:** Max 3 self-healing retry iterations. If parity remains unverified, graceful degradation exposes the test diffs to the user for manual checkpoint review.

---

## 7. Phased Implementation Roadmap

* **Phase 1 (Core Engine & Disassembler):** Local Docker runner, `r2pipe`/`objdump` inspector module, Go runtime filter.
* **Phase 2 (LangGraph Multi-Agent Loop):** Graph construction, Gemini 2.5 Flash prompt orchestration, dynamic probe execution.
* **Phase 3 (Differential Verifier & Repair Loop):** Automated test vector generator, dual-execution harness, repair feedback loop.
* **Phase 4 (Web Dashboard & Streaming UX):** FastAPI SSE endpoints, React/Tailwind visualizer, side-by-side diff viewer.
* **Phase 5 (E2E Validation with `aegis` CLI):** Verification against real compiled C and Go binaries, video demo recording preparation.
