# Phone flight game

Read `docs/INTERFACE.md` before changing RTL, bridge, or controls. The coordinator assigns disjoint paths in `WORKPLAN.md`; only the coordinator edits shared specs, Git state, and integration tests.

- Keep SKY130/ttsky26d process settings and physical checks unless an organizer confirms a different shuttle. Three tiles is a budget, not permission to use six. Use a legal footprint within budget.
- One 25.2 MHz clock; update gameplay only at vertical blank. Preserve Tiny VGA outputs and leave all uio pins as inputs.
- Phone preprocessing belongs to the host bridge; chip consumes bounded integer control packets. Preserve raw Android sensor/recording behavior.
- Read `docs/PLATFORM.md` for template/process evidence and `docs/WIRING.md` before any physical connection.
- Run unit, UART, gameplay, VGA, replay, and physical checks separately. A green layout does not prove gameplay. Record actual results and hardware blockers.
- Manufacturing submission, payment, and legal acceptance require explicit user authorization.
