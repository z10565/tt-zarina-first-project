# Work and ownership

Coordinator: /root, branch `feat/phone-flight-game`. All edits are isolated from main. Workers request ownership changes before overlapping paths; only root runs Git mutations and updates this table/specs.

| Work | Owner | Write paths | Status |
| --- | --- | --- | --- |
| Interface, integration, UART/parser/button/VGA, tests, docs | /root | src/project.v, src/uart_rx.v, src/control_packet.v, src/fire_button.v, src/vga_timing.v, test/, scripts/, docs/ except PLATFORM.md, README.md, WORKPLAN.md, AGENTS.md, .gitignore | active |
| Bounded game and pixel renderer | game-worker | src/flight_game.v, src/pixel_renderer.v | assigned |
| Phone live transport + PC preprocessing/serial/replay | bridge-worker | bridge/, ../usb c accelerometer/app/; app docs only by root | assigned |
| Official SKY migration / CI / platform evidence | platform-worker | .github/, .devcontainer/, info.yaml, src/config.json, docs/PLATFORM.md, NOTICE | assigned |

Worker handoff: changed paths, behavior, tests run/results, unrun checks, blockers, next action. No takeover until prior owner stops. Independent phone and physical-board validation remain pending until a device is connected.
