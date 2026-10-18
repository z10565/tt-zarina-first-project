`timescale 1ns/1ps
module tb_integration;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,ena=1;reg[7:0] ui=8;
 wire[7:0] uo,uio,oe;
 tt_um_zarina_phone_flight dut(ui,uo,8'b0,uio,oe,ena,clk,rst_n);
 task cycles(input integer n);repeat(n)@(negedge clk);endtask
 function[7:0] crc8(input[7:0] c0,input[7:0] value);reg[7:0]c;integer i;
 begin c=c0^value;for(i=0;i<8;i=i+1)c=c[7]?(c<<1)^8'h07:c<<1;crc8=c;end endfunction
 task uart_byte(input[7:0]value);integer b;begin
  ui[3]=0;cycles(219);for(b=0;b<8;b=b+1)begin ui[3]=value[b];cycles(219);end ui[3]=1;cycles(219);
 end endtask
 task packet(input[7:0]seq,input[7:0]flags);reg[7:0]c;begin
  c=crc8(0,seq);c=crc8(c,1);c=crc8(c,0);c=crc8(c,2);c=crc8(c,flags);
  uart_byte(8'ha5);uart_byte(8'h5a);uart_byte(seq);uart_byte(1);uart_byte(0);uart_byte(2);uart_byte(flags);uart_byte(c);cycles(4);
 end endtask
 task next_frame;begin
  while(!dut.frame_tick)@(negedge clk);
  @(negedge clk);
 end endtask
 reg[7:0] saved_x;reg[6:0]saved_y;
 initial begin
  cycles(4);rst_n=1;cycles(4);
  saved_x=dut.enemy_x;next_frame();next_frame();
  if(dut.enemy_x!=saved_x || dut.link_valid)$fatal(1,"no-input safety pause violated");
  $display("REPRO: VGA frame ticks run, but no UART packets => game intentionally paused");
  packet(1,1);
  if(!dut.link_valid)$fatal(1,"top UART control link");
  dut.game.game_over=1;
  packet(2,3);
  if(!dut.restart_pending || !dut.game_over)$fatal(1,"restart pulse not retained between frames");
  next_frame();if(dut.game_over || dut.player_x!=24 || dut.restart_pending)$fatal(1,"packet restart not applied atomically");
  next_frame();if(dut.player_x!=25 || dut.enemy_x!=151)$fatal(1,"packet restart repeated or frame movement absent");
  dut.game.game_over=1;ui[0]=1;cycles(126010);
  if(!dut.fire_pending || !dut.fire_level)$fatal(1,"top physical debounce/event pending");
  next_frame();if(dut.game_over || dut.player_x!=24)$fatal(1,"physical restart lost");
  next_frame();if(dut.player_x!=25 || !dut.bullet_active)$fatal(1,"held fire path or duplicate restart");
  packet(3,0);saved_x=dut.player_x;saved_y=dut.player_y;
  next_frame();next_frame();
  if(dut.link_valid || dut.player_x!=saved_x || dut.player_y!=saved_y)$fatal(1,"disconnect moved top-level game");
  if(oe!==0 || uio!==0 || ^uo===1'bx)$fatal(1,"unknown/unsafe top outputs");
  ena=0;cycles(4);if(uo!==8'h88 || oe!==0)$fatal(1,"enable contract");
  $display("PASS: production UART -> atomic controls -> frame latches, physical fire/restart, disconnect and enable");$finish;
 end
 initial begin #100000000;$fatal(1,"integration timeout");end
endmodule

