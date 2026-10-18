# Work and ownership

Coordinator: /root, branch `fix/board-bringup-diagnostics`, based on verified `feat/phone-flight-game`. All edits are isolated from main. Workers request ownership changes before overlapping paths; only root runs Git mutations and updates this table/specs.

| Work | Owner | Write paths | Status |
| --- | --- | --- | --- |
| Interface, UART/parser/button/VGA, integration tests | Unassigned | None | Implemented and integrated; local checks pass; final CI tracked in release |
| Bounded game and pixel renderer | Unassigned | None | Implemented, tested and reviewed; worker released ownership |
| Phone live transport + PC preprocessing/serial/replay | Unassigned | None | Implemented; Android branch feat/flight-bridge at 537a7fa; workers released ownership |
| Official SKY migration / CI / platform evidence | Unassigned | None | Migrated and integrated; worker released ownership |
| Physical FPGA/phone/VGA bring-up | Unassigned | None | Awaiting attached hardware and revision/firmware identification; follow docs/FPGA.md |
| Organizer shuttle and footprint confirmation | Unassigned | None | Required before manufacturing submission |
| Standalone USB relay/startup | Unassigned | None | Implemented;17 mocked-host tests pass; physical USB/startup bypass/power/firmware validation pending |
| Standalone integration | Unassigned | None | Kotlin mapping matches371 app+145 synthetic Python packets; Android USB transport implemented; docs/STANDALONE.md; no RTL changed |

Worker handoff: changed paths, behavior, tests run/results, unrun checks, blockers, next action. No takeover until prior owner stops. Independent phone and physical-board validation remain pending until a device is connected.

Implementation workers have finished; no worker retains a write claim. A future coordinating session should assign fresh, disjoint paths before editing. This ledger is not an atomic lock across independent sessions.

## Active bring-up assignment (2026-10-18 UTC)

/root owns fpga/, test/tb_integration.v, test/tb_replay.v, scripts/check_board_demo.py, scripts/run_checks.sh, docs/FPGA.md and WORKPLAN.md. Reproduce no-input static screen, add temporary deterministic UART demo, and verify SDK startup. Existing RTL/protocol/shuttle settings stay fixed. No workers assigned.


Local evidence: no-packet motion expectation reproduced static state while real VGA ticks advance; valid packets resume enemy/player movement in top-level simulation. 21 board helper tests pass. Board demo physical test pending; user confirmed independent self-test animation only.


2026-10-18 follow-up: user reports board_demo animates on real FPGA. /root owns fpga/standalone.py, fpga/test_standalone.py, docs/STANDALONE.md and WORKPLAN.md for verified re-enable operation and phone handoff; phone USB/handshake/power still awaiting observation. Prior diagnostic revision 40d87de passed test, FPGA, docs and GDS/precheck/gate-level workflows.

