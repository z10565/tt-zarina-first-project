# Work and ownership

Coordinator: /root, branch `feat/standalone-usb`, based on verified `feat/phone-flight-game`. All edits are isolated from main. Workers request ownership changes before overlapping paths; only root runs Git mutations and updates this table/specs.

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
