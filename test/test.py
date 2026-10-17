"""Top-level pin contract, works unchanged on flattened gate-level netlist."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer


@cocotb.test()
async def pin_and_vga_contract(dut):
    dut.clk.value = 0
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 8  # idle-high RX, fire released
    dut.uio_in.value = 0
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await Timer(205, unit="ns")
    assert int(dut.uo_out.value) == 0x88
    dut.rst_n.value = 1
    # First line visible/blank and exact sync edges: avoid any internal handles in GL.
    await Timer(26_080, unit="ns")  # 652 cycles into line
    assert int(dut.uo_out.value) & 0x88 == 0x88
    await Timer(320, unit="ns")
    assert int(dut.uo_out.value) & 0x80 == 0
    assert int(dut.uo_out.value) & 0x77 == 0  # RGB blank during sync
    await Timer(3_840, unit="ns")
    assert int(dut.uo_out.value) & 0x80 == 0x80
    assert int(dut.uio_oe.value) == 0 and int(dut.uio_out.value) == 0
    dut.ena.value = 0
    await Timer(200, unit="ns")
    assert int(dut.uo_out.value) == 0x88
    assert int(dut.uio_oe.value) == 0
