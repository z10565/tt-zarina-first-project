# Phone Flight — RTU Chipathon

Synthesizable Tiny Tapeout flight/shooting game: phone tilt flies the plane, rotation aims a five-direction cannon, and a separate physical button fires. Procedural VGA graphics, one enemy/projectile, score, collisions, game over and restart.

The same RTL targets the **ETR FPGA ASIC simulator first**, and SKY130 Tiny Tapeout later. The existing TT.RUN.09 ASIC is not reprogrammable. Selected standard footprint: **1x2 = two tiles**, within the three-tile budget. The matching template lists no three-tile shape; `3x2` would be six tiles. Organizer confirmation remains required before submission.

## Start here

- [Interface/game specification](docs/INTERFACE.md)
- [FPGA build, upload and onboard USB relay](docs/FPGA.md)
- [Protocol, controls and PC bridge](bridge/README.md)
- [Wiring and voltages](docs/WIRING.md)
- [Process/template evidence](docs/PLATFORM.md)
- [Verification and blockers](docs/VERIFICATION.md)
- [Tiny Tapeout datasheet](docs/info.md)

```text
Phone app raw JSONL -> USB ADB forwarding -> PC calibration/filtering
 -> CRC-protected UART packets -> ETR USB CDC/UART relay -> ui3
 -> game RTL -> Tiny VGA OUTPUT PMOD -> monitor
Physical button -> ui0
```

No USB/radio stack exists in silicon. VGA uses every dedicated output. All bidirectional outputs remain disabled.

## Run locally

Linux/WSL, Python3.11, Icarus, Verilator, Yosys and Make:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r test/requirements.txt
python -m unittest discover -s bridge/tests -v
python -m unittest discover -s fpga -p 'test*.py' -v
bash scripts/run_checks.sh
make -C test
python -m cocotb_tools.check_results test/results.xml
```

The checks generate five RTL preview PNGs under `test/output/` and replay captured app packets through UART/parser RTL. Official SKY workflows retain gate-level, GDS/precheck, documentation and FPGA builds. Layout success alone does not prove gameplay.

No shared shuttle assembly or another team's design is edited. Work stays on an isolated branch. Passing workflows prepare artifacts; they do not perform manufacturing submission, payment or legal acceptance.

Original Apache-2.0 [LICENSE](LICENSE) retained; see [NOTICE](NOTICE).
