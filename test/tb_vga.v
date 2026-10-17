`timescale 1ns/1ps
module tb_vga;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 wire[9:0] x,y;wire active,hs,vs,frame_tick;
 vga_timing dut(clk,rst_n,x,y,active,hs,vs,frame_tick);
 integer xx,yy,visible=0,hslow=0,vslow=0,ticks=0;
 initial begin
  repeat(2)@(negedge clk);rst_n=1;
  for(yy=0;yy<525;yy=yy+1)for(xx=0;xx<800;xx=xx+1)begin
   if(x!=xx || y!=yy)$fatal(1,"raster coordinate %d,%d versus %d,%d",x,y,xx,yy);
   if(active !== (xx<640 && yy<480))$fatal(1,"active mismatch");
   if(hs !== !(xx>=656 && xx<752))$fatal(1,"HSYNC polarity/timing");
   if(vs !== !(yy>=490 && yy<492))$fatal(1,"VSYNC polarity/timing");
   if(frame_tick !== (xx==0 && yy==480))$fatal(1,"game update not vertical blank");
   visible=visible+active;hslow=hslow+!hs;vslow=vslow+!vs;ticks=ticks+frame_tick;
   @(negedge clk);
  end
  if(x!=0 || y!=0 || visible!=307200 || hslow!=50400 || vslow!=1600 || ticks!=1)$fatal(1,"line/frame totals");
  $display("PASS: all 420000 VGA clocks, negative sync, porches, blanking enable and frame wrap");$finish;
 end
endmodule
