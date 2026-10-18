`timescale 1ns/1ps
module tb;
 reg clk; reg rst_n; reg ena; reg [7:0] ui_in; reg [7:0] uio_in;
 wire [7:0] uo_out,uio_out,uio_oe;
`ifdef GL_TEST
 supply1 VPWR;
 supply0 VGND;
`endif
 initial begin $dumpfile("tb.fst");$dumpvars(0,tb);end
 tt_um_zarina_phone_flight user_project (
`ifdef GL_TEST
    .VPWR(VPWR),.VGND(VGND),
`endif
    .clk(clk),.rst_n(rst_n),.ena(ena),.ui_in(ui_in),.uo_out(uo_out),
    .uio_in(uio_in),.uio_out(uio_out),.uio_oe(uio_oe));
endmodule
