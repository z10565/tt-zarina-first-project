# Platform and migration evidence

## Process and template

This repository originally used the SKY Wokwi template, with `yaml_version: 6`, `language: Wokwi`, `clock_hz: 0`, one tile and `ttsky26d` workflows targeting `sky130A`. The flight implementation deliberately migrates to the matching [official SKY Verilog template](https://github.com/TinyTapeout/ttsky-verilog-template/tree/a42e6662fab316e93b4e26399e21d41664a460b7), revision `a42e6662fab316e93b4e26399e21d41664a460b7`, inspected 2026-10-17. Its Apache 2.0 LICENSE remains unchanged; NOTICE records attribution. Original Wokwi attribution remains in Git history.

Metadata now selects Verilog, explicit top/source files and a nonzero clock. Wokwi IDs and remote netlist fetching are absent from the active build path. Workflows and devcontainer files come from this official revision. Process-specific GDS, precheck, documentation and optional FPGA actions remain `@ttsky26d`, with GDS explicitly `pdk: sky130A`. No shared shuttle configuration or other project is edited.

**Organizer decision required before submission:** confirm this group's actual event shuttle is SKY130/ttsky26d, its tile entitlement and permitted footprint, and its physical demo board/clock source. The repository is evidence of the existing process selection; it is not an event booking or organizer confirmation. Do not migrate to IHP/GF merely because another template exists.

## Footprint

The official revision's info.yaml lists `1x1`, `1x2`, `2x2`, `3x2`, `4x2`, `6x2`, `8x2`. None has exactly three tiles. This design selects **1x2 = two tiles**, within the three-tile group budget. `3x2` consumes six tiles and is forbidden by the budget. The unused third tile does not enlarge this macro. Ask organizers whether a custom three-tile macro or separate third project is allowed if needed; do not assume either. Area and routing must pass in 1x2 before claiming fit. The [official FAQ](https://tinytapeout.com/faq/) explains the next standard size above 1x1 is 1x2 and metadata changes drive layout.

## Clock and VGA

The target clock is **25,200,000 Hz**, constrained at `39.682539683 ns` in src/config.json. It gives exact 60 Hz for the 800x525 raster (640x480 active), negative sync, with no generated internal clock. [Official clock specifications](https://tinytapeout.com/specs/clock/) describe external clk and an approximately 66 MHz SKY pad input limit. This supports the requested frequency range, but is not timing closure: routed STA at the selected PVT corners remains necessary.

An RP2040's divider may produce an approximation rather than exact 25.2 MHz. Measure/report the actual supplied frequency and confirm monitor lock and UART margin on the exact board. Do not silently use a 50 MHz board default. VGA outputs use the [official Tiny VGA mapping](https://tinytapeout.com/specs/pinouts/); all eight dedicated outputs are occupied, so no UART TX is assigned. UART RX uses the documented ui_in[3] option. All uio output enables stay zero.

## Electrical limits and hardware blockers

The [official GPIO specifications](https://tinytapeout.com/specs/gpio/) distinguish SKY130 core logic from physical board I/O: standard demo board I/O is 3.3 V and **not 5 V tolerant**, with nominal 4 mA drive and rated input/output frequencies 66/33 MHz. A binary 1 is not 1 V. The external UART must be 3.3 V TTL/CMOS, never RS-232 voltage levels; common ground is required. A Tiny VGA resistor adapter converts digital RGB levels for the VGA analog input; do not wire GPIO directly to analog RGB without the correct adapter.

User photos subsequently identify a white TinyTapeout06+ demo board with an existing TT.RUN.09 ASIC carrier, a separate purple ETR demo board with an FPGA ASIC simulator, and a Tiny VGA v1.2 adapter. These are visual identifications rather than a measured electrical validation; the simulator PCB revision and firmware still require confirmation. Their connector orientation, voltage, pull resistors, source selection and clock programming remain unverified. Read WIRING.md and identify exact boards before connecting; do not rely on legacy QFN pin numbers for an unknown board. Phone sensors reach RTL only through the documented host bridge; this macro includes no USB, radio or direct phone interface.

## CI preservation and diagnosis

The pre-existing documentation run [38909008037](https://github.com/z10565/tt-zarina-first-project/actions/runs/38909008037) failed because the entire pinout was blank. Populated game pin metadata fixes that cause. Official docs/GDS/precheck workflows remain active. The official viewer artifact/deployment action is retained for the default branch; isolated branches run layout and precheck without deploying the public viewer. FPGA builds now run on every push using the official ICE40 action, pinned support tools and a 25.2 MHz nextpnr timing constraint; see FPGA.md. No physical check is replaced by a gameplay test or waived to obtain green CI.

The functional workflow adds bridge unit tests and scripts/run_checks.sh, then uses the official Icarus/cocotb test invocation and explicit results.xml failure check. Record final test, routed timing, area, precheck and documentation results for the same final commit in the verification report. A green layout is not evidence of gameplay, and neither CI nor a push submits manufacturing.

References: [HDL guide](https://tinytapeout.com/hdl/), [technical specifications](https://tinytapeout.com/specs/), [pinouts](https://tinytapeout.com/specs/pinouts/), [FAQ](https://tinytapeout.com/faq/).
