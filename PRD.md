## **Product Requirements Document: Scion Multi-Material Printer Controller V1.0**

**Version:** 1.0
**Date:** September 26, 2025
**Author:** AI Architect
**Status:** Draft  
**Document Owner:** AI Architect / Engineering Lead  

### Executive Summary (Added)
A Raspberry Pi–based controller orchestrates multi-material resin prints by monitoring printer layer progression and triggering timed vat drain/fill sequences using an MMU (pump array). V1.0 targets reliability, configurability, and a modern web UI replacing the legacy Qt tool. Success depends on deterministic material change execution, recoverability from transient faults, and clear operator feedback.

### Revision History (Added)
| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 0.9 | 2025-09-26 | AI Architect | Initial draft |
| 1.0-draft2 | 2025-09-29 | AI Architect | Structural refinement, acceptance criteria, NFR expansion |

### 1. Introduction

The Scion Multi-Material Printer Controller is a hardware and software system designed to enable automated multi-material resin 3D printing on the Anycubic Photon series. The system uses a Raspberry Pi to orchestrate communication between the 3D printer and a custom Multi-Material Unit (MMU) hardware, which automates the process of draining and refilling the resin vat at specific layer heights defined by the user.

This document outlines the requirements for Version 1.0, which focuses on delivering a stable, reliable, and user-friendly experience primarily through a modern web-based interface.

### 2. Product Goals & Objectives

The primary goal of this project is to create a reliable and accessible tool for researchers and technicians to conduct multi-material 3D printing experiments.

*   **Objective 1: Automate the Multi-Material Workflow:** Provide a "set it and forget it" system that reliably executes a pre-defined sequence of material changes over the course of a long print job.
*   **Objective 2: Ensure System Stability:** The software must be robust enough to run for 24+ hours without crashing and gracefully handle common errors like temporary network disconnects.
*   **Objective 3: Provide a User-Friendly Interface:** The primary interface (web application) must be intuitive for non-developers, allowing for easy recipe creation, print monitoring, and manual control.
*   **Objective 4: Deliver Clear, Real-Time Feedback:** The user must always have a clear understanding of the system's current state, the action it is performing, and a log of past events.
*   **Objective 5 (Added):** Provide auditable logs enabling post-run reconstruction of every material change event.

### 3. User Personas

**1. Dr. Elena Vance (Research Scientist)**
*   **Role:** Primary user who designs the multi-material experiments.
*   **Goals:** Wants to create multi-material prints with new formulations. Needs a reliable tool to execute her print plans with high precision and repeatability.
*   **Technical Skill:** Tech-savvy, understands the printing process intimately, but is not a software developer.
*   **Needs:** A powerful and flexible recipe creation system; detailed logs for post-print analysis; confidence that the system will execute the plan without failure.

**2. Ben Carter (Student)**
*   **Role:** Operator responsible for setting up the hardware, loading materials, starting the print, and performing maintenance.
*   **Goals:** Wants to get a print started quickly and efficiently. Needs to be able to diagnose and fix simple problems without escalating.
*   **Technical Skill:** Mechanically inclined, comfortable with basic software interfaces.
*   **Needs:** A simple, step-by-step process for starting a print; clear status indicators; straightforward manual controls for priming pumps and cleaning; unambiguous error messages.

### 4. System Architecture Overview

The system consists of three main software components running on a Raspberry Pi, which communicates with two hardware endpoints.

```
+------------------+     +-------------------+     +--------------------+
| Web Interface    |     |   Flask Web App   |     |    Print Manager   |
| (Browser/Mobile) | <-->| (app.py)          | <-->|   (print_manager.py)|
+------------------+     +-------------------+     | (Background Service) |
                               |                   +----------+---------+
                               |                              |
                +--------------+--------------+               |
                | Inter-Process Communication |               |
                |    (shared_status.py)     |               |
                +-----------------------------+               |
                                                              |
                 +---------------------------+----------------+-----------+
                 |                           |                            |
      +----------v-----------+      +--------v--------+         +---------v---------+
      | MMU Control Module   |      | Printer Comms   |         | Logging Module    |
      | (mmu_control.py)     |      | (printer_comms.py)|         | (logging_config.py)|
      +----------+-----------+      +---------+-------+         +-------------------+
                 |                            |
     +-----------v----------+      +----------v---------+
     | MMU Hardware (Pumps) |      | 3D Printer (Wi-Fi) |
     +----------------------+      +--------------------+
```

#### 4.1 Logical Components (Refined)
* Web Interface (SPA or server-rendered hybrid) – real-time dashboard, configuration, control.
* Flask Backend – REST + Server-Sent Events (SSE) or WebSocket push (implementation decision) for status streaming.
* Print Manager Service – long-running supervisor (loop interval: 2–5 s) executing recipe logic.
* Shared Status Module – single source of truth (in-memory + persisted snapshot file on graceful shutdown).
* MMU Control – abstracts GPIO / pump actuation / safety interlocks.
* Printer Comms – abstraction over `uart-wifi` with retry + backoff.
* Logging Module – structured logging (JSON lines + human-readable rolling log).

#### 4.2 State Definitions (Added)
Print Manager High-Level States:
IDLE -> MONITORING -> (MATERIAL_CHANGE | ERROR | STOP_REQUESTED) -> MONITORING -> COMPLETED / ABORTED
Material Change Sub-States:
REQUEST_PAUSE -> WAIT_PLATE_CLEAR -> DRAINING -> FILLING -> SETTLING -> REQUEST_RESUME -> COMPLETE
Error States (non-fatal auto-recoverable): TRANSIENT_PRINTER_DISCONNECT, COMMAND_TIMEOUT  
Fatal (requires operator): CONFIG_INVALID, PUMP_ACTUATION_FAILURE, RECIPE_CONFLICT

#### 4.3 Data Persistence (Added)
* Configuration Files: canonical; edits atomically written via temp + rename.
* Runtime Cache: in-memory dict; periodically (every 60 s) snapshot to `runtime_status.json`.
* Logs: `logs/app.log` (rotating, 10 MB * 5). Material change events also mirrored to `logs/material_events.jsonl`.

### 5. Features & Functional Requirements
(Normalized requirement IDs; added Acceptance Criteria (AC).)

#### 5.1 Feature 1: System Configuration

*   **User Story (Ben):** "As a Student, I want a single place to configure the printer's IP address and the physical profiles of our pumps so that I can set up new hardware easily."

*   **Requirements:**
    *   **FR-1.1:** The system MUST read network settings from `config/network_settings.ini` at backend startup and on explicit reload.
      *   **AC:** Editing via UI then pressing "Save" and "Reload" updates in-memory values without backend restart.
    *   **FR-1.2:** The system MUST read pump profiles (flow rates, pins) and material change parameters (drain volume, fill volume) from `config/pump_profiles.json`.
      *   **AC:** Invalid JSON => validation error surfaced; file not overwritten.
    *   **FR-1.3:** The UI MUST allow view/edit with client-side validation (required fields, numeric ranges).
      *   **AC:** Submitting invalid form blocks save; no partial file writes.
    *   **FR-1.4:** "Test Connection" MUST attempt printer status query (timeout ≤ 3 s).
      *   **AC:** Success => green status with round-trip time; failure enumerates cause (DNS, timeout, protocol).
    *   **FR-1.5 (Added):** Config changes MUST be versioned (increment integer revision persisted in file comment).
      *   **AC:** Revision increments visible in UI after save.

#### 5.2 Feature 2: Recipe Management

*   **User Story (Elena):** "As a research scientist, I want to create, save, and load a recipe that specifies which material to use at which layer number, so I can design my experiments."

*   **Requirements:**
    *   **FR-2.1:** The web interface MUST provide a "Recipe Builder" page to add, edit, and remove material change steps (`Material`, `Layer Number`).
      *   **AC:** UI adds/removes steps; ordering auto-sorted ascending by layer.
    *   **FR-2.2:** The recipe MUST be saved to `config/recipe.txt` in the format `A,50:B,120:C,200`.
      *   **AC:** Loading file reconstructs identical step list.
    *   **FR-2.3:** The UI MUST validate user input to prevent duplicate layer numbers and ensure valid materials (A, B, C, D) are selected.
      *   **AC:** Duplicate layer input rejected with inline message.
    *   **FR-2.4:** The system MUST be able to import a recipe from a raw text string.
      *   **AC:** Malformed => error; valid => preview before overwrite.
    *   **FR-2.5 (Added):** Backend parses recipe at print start producing immutable execution plan.
      *   **AC:** Mid-print edits do NOT affect active run (warning displayed).
    *   **FR-2.6 (Added):** Layer numbers MUST be strictly increasing; zero or negative invalid.
      *   **AC:** Attempt to add layer 0 rejected.

#### 5.3 Feature 3: Automated Multi-Material Print Execution

*   **User Story (Ben):** "As a Student, after selecting a file on the printer and loading a recipe, I want to press a single 'Start' button and have the system manage the entire multi-material print process automatically."

*   **Requirements:**
    *   **FR-3.1:** The web application MUST manage a persistent background process (`print_manager.py`) to orchestrate the print.
      *   **AC:** Persistent service uses watchdog thread detecting stalled loop (>10 s delay).
    *   **FR-3.2:** Upon starting, the `print_manager` service MUST continuously poll the printer for its status (specifically the current layer number).
      *   **AC:** Poll interval configurable (default 3 s; range 1–10 s).
    *   **FR-3.3:** When the current layer matches a layer in the recipe, the system MUST automatically execute the **Material Change Sequence**:
        1.  Send a `pause` command to the printer.
        2.  Wait a pre-configured duration for the build plate to rise clear of the vat.
        3.  Activate the drain pump to remove the old material.
        4.  Activate the correct fill pump to add the new material.
        5.  Wait a pre-configured duration for the material to mix and settle.
        6.  Send a `resume` command to the printer.
      *   **AC:** Material Change Sequence (Atomic):
        1. Pause printer (retry x3 w/ exponential backoff 0.5/1/2 s).
        2. Wait (config: `plate_clear_delay_s`).
        3. Drain pump run until computed duration = drain_volume_ml / drain_rate_ml_per_s (±5% tolerance).
        4. Fill pump run similarly (selected material).
        5. Settling delay (`settle_delay_s`).
        6. Resume printer (retry x3).
    *   **FR-3.4:** The system MUST only perform a material change for a given layer *once*.
      *   **AC:** Each sub-step logged with start/end timestamp and success/failure.
    *   **FR-3.5 (Added):** If printer layer regresses >2 layers unexpectedly, system enters ERROR (CAUSE: LAYER_ROLLBACK).
    *   **FR-3.6 (Added):** Manual stop of multi-material manager leaves printer state untouched.
      *   **AC:** Confirm dialog; status -> IDLE.

#### 5.4 Feature 4: Real-Time Monitoring and Control

*   **User Story (Elena):** "As a researcher, while a multi-material print is running, I want to see a live dashboard with the printer's status, current layer, active material, and a log of events, so I can have confidence my experiment is proceeding correctly."

*   **Requirements:**
    *   **FR-4.1:** The web interface dashboard MUST display the following information, updated in real-time (<= 5-second latency):
        *   Printer Connection Status (Connected/Disconnected)
        *   Printer State (Printing, Paused, Idle)
        *   Current Layer / Total Layers
        *   Print Progress (%)
        *   Multi-Material Process State (e.g., Monitoring, Draining, Filling, Paused)
      *   **AC:** Update latency target ≤5 s (stretch ≤2 s). Mechanism: SSE or WebSocket; fallback to polling.
    *   **FR-4.2:** The UI MUST include an activity log that shows timestamped events from the `print_manager` and other backend modules.
      *   **AC:** Activity log filterable by category (SYSTEM, MATERIAL_CHANGE, ERROR, USER_ACTION).
    *   **FR-4.3:** The user MUST be able to stop the multi-material monitoring process without stopping the underlying print job on the printer.
    *   **FR-4.4:** The user MUST be able to send manual `pause`, `resume`, and `stop` commands to the printer at any time from the web interface.
      *   **AC:** Manual commands require confirmation for STOP; pause/resume immediate.
    *   **FR-4.5 (Added):** Progress bar displays % = current_layer / max(recipe last layer, printer total) * 100.
      *   **AC:** Rounds to single decimal.
    *   **FR-4.6 (Added):** Current Active Material derived from last change executed; defaults to INITIAL (configured).
      *   **AC:** BEFORE first change shows INITIAL.

#### 5.5 Feature 5: Manual Hardware Control & Diagnostics

*   **User Story (Ben):** "As a Student, I need to be able to run any pump manually for a specific amount of time to prime the lines or perform maintenance."

*   **Requirements:**
    *   **FR-5.1:** The "Manual Controls" page MUST allow the user to select any pump (A, B, C, Drain), a direction (Forward/Reverse), and a duration in seconds.
      *   **AC:** Duration bounds: 0.5–120 s; default 5 s.
    *   **FR-5.2:** Executing a manual pump command MUST immediately run the specified pump for the given duration.
      *   **AC:** Pump safety: Only one pump may run simultaneously (enforced mutex).
    *   **FR-5.3:** The system MUST have a global **Emergency Stop** button that immediately halts all pump activity.
      *   **AC:** Emergency Stop clears GPIO, sets SAFETY_LOCK for 3 s.
    *   **FR-5.4 (Added):** Dry-run diagnostic mode simulates timing without GPIO activation.
      *   **AC:** Log entries marked SIMULATION.

### 6. Non-Functional Requirements (Expanded)

*   **NFR-1 (Reliability):** The `print_manager` service must run without crashing for the duration of a multi-day print. It must attempt to reconnect to the printer at least 3 times if a connection is lost before entering an error state.
*   **NFR-2 (Usability):** The web interface must be responsive and functional on both desktop browsers and mobile/tablet devices.
*   **NFR-3 (Performance):** Web page load time should be under 3 seconds on the local network. Real-time status updates on the dashboard should have a latency of no more than 5 seconds from the actual event.
*   **NFR-4 (Maintainability):** All configuration (network, pumps) must be stored in external files and not hard-coded. Backend modules must have clear, single responsibilities.
*   **NFR-5 (Logging):** Structured JSON + human-readable; p95 write latency <10 ms.
*   **NFR-6 (Safety):** Pumps cannot exceed configured max continuous runtime (default 180 s) even via repeated manual calls (rolling window).
*   **NFR-7 (Configuration Integrity):** Writes are atomic (temp file + fsync + rename).
*   **NFR-8 (Security Posture - Local):** Web UI session authenticated via simple shared admin token (configurable) for V1.0; no open CORS.
*   **NFR-9 (Observability):** Health endpoint `/health` returns composite status (printer reachable, manager state, last loop timestamp delta).
*   **NFR-10 (Time Sync Assumption):** System clock must be NTP-synchronized; if drift >60 s detected, log WARNING.

### 7. Assumptions & Dependencies

*   **Assumptions:**
    *   The MMU hardware (pumps, controllers, wiring) is correctly assembled and functional.
    *   The Raspberry Pi, 3D printer, and ESP32 gateway are powered on and connected to the same isolated Wi-Fi network.
*   **Dependencies:**
    *   Python 3.7+
    *   All libraries listed in `requirements.txt` and `web-app/requirements.txt`.
    *   A functioning `uart-wifi` library for printer communication.
    *   (Added) If `uart-wifi` library lacks async support, wrapper will provide thread-based non-blocking pattern.

### 8. Out of Scope for V1.0

*   Slicer integration or modification of print files.
*   Cloud connectivity or remote access outside the local network.
*   Support for multiple printers from a single interface.
*   Advanced sensor feedback (e.g., vat level sensors, flow meters).
*   The legacy C++ Qt GUI will be considered deprecated and will not receive new features. It only needs to remain minimally functional for legacy users.

### 9. Success Metrics (Refined)
* Print Success Rate: >95% multi-material jobs finish without FR-3.* fatal error (evaluated over rolling 30 jobs).
* Mean Material Change Execution Variance: Timing within ±7% planned duration.
* UI Adoption: ≥90% of new sessions originate from web UI vs legacy (analytics counter).
* New User Onboarding: Technician completes first full run in ≤15 minutes (scripted usability test).
* MTTR (recoverable network drop): ≤2 minutes average (automatic reconnect).

### 10. Traceability Matrix (Added - Summary)
Feature 1: FR-1.1–1.5 -> NFR-7, NFR-4  
Feature 2: FR-2.1–2.6 -> NFR-4, NFR-1  
Feature 3: FR-3.1–3.6 -> NFR-1, NFR-5, NFR-9  
Feature 4: FR-4.1–4.6 -> NFR-3, NFR-5  
Feature 5: FR-5.1–5.4 -> NFR-6, NFR-5

### 11. Error Handling & Recovery (Added)
| Error | Detection | Retry Strategy | Escalation |
|-------|-----------|----------------|------------|
| Printer unreachable | Timeout | 3 tries exponential | ERROR state after 3; user alert |
| Pause/Resume failed | Non-200 / no ack | 3 retries | ERROR: COMMAND_FAILURE |
| Pump actuation failure | GPIO exception / current sensor (future) | None | FATAL: requires operator |
| Recipe parse fail | Load attempt | N/A | Block start |
| Layer stagnation (>5 polls same layer while printer says PRINTING) | Poll loop | 2 additional polls | WARNING; continue |

### 12. System State Machine (Added)
(Descriptive)
IDLE -> (Start) -> MONITORING  
MONITORING -> (Layer == Target) -> MATERIAL_CHANGE  
MATERIAL_CHANGE -> (Success) -> MONITORING  
Any -> (Emergency Stop) -> ABORTED  
Any -> (Fatal Error) -> ERROR -> IDLE (after acknowledge)

### 13. Risks & Mitigations (Added)
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Network instability | Missed layer triggers | Medium | Retry + tolerance window (allow up to 2 missed polls) |
| Pump calibration drift | Incorrect volumes | Medium | Add manual calibration run + log actual durations |
| User edits recipe mid-run | Inconsistent execution | High | Lock active recipe; display warning |
| File corruption (power loss during write) | Config loss | Low | Atomic write strategy |
| Clock drift | Log mis-sequencing | Low | NTP check + warning |

### 14. Glossary (Added)
* MMU: Multi-Material Unit controlling pumps.
* Recipe: Ordered mapping layer -> material.
* Material Change Sequence: Defined atomic steps FR-3.3.
* Active Material: Last successfully filled material designation.
* Execution Plan: Immutable snapshot of recipe at run start.

### 15. Open Issues (Added)
1. Decide between SSE vs WebSocket for streaming (performance test pending).
2. Need calibration utility for pump flow-rate derivation (V1.1 candidate).
3. Authentication hardening (JWT or per-user) future scope.
4. Consider adding checksum to recipe file for integrity validation.

### 16. Appendix (Optional Future)
Potential future enhancements: sensor integration, multi-printer orchestration, remote cloud sync.

---  
End of Document (Refined V1.0 Draft)