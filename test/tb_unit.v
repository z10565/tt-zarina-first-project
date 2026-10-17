`timescale 1ns/1ps
module tb_unit;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 task cycles(input integer n); repeat(n) @(negedge clk); endtask
 task check(input reg ok,input string message); if(!ok) $fatal(1,"%s",message); endtask
 task reset_all; begin rst_n=0; cycles(4); rst_n=1; cycles(2); end endtask

 reg rx=1;
 wire [7:0] rx_data; wire rx_valid,rx_error;
 integer rx_count=0,error_count=0; reg [7:0] last_rx;
 uart_rx #(.CLKS_PER_BIT(8)) uart(clk,rst_n,rx,rx_data,rx_valid,rx_error);
 always @(posedge clk) if(!rst_n) begin rx_count<=0; error_count<=0; last_rx<=0; end
 else begin if(rx_valid) begin rx_count<=rx_count+1;last_rx<=rx_data;end if(rx_error)error_count<=error_count+1; end
 task serial_byte(input [7:0] value,input reg bad_stop);
 integer i; begin rx=0;cycles(8);for(i=0;i<8;i=i+1)begin rx=value[i];cycles(8);end rx=!bad_stop;cycles(8);end endtask

 reg [7:0] data=0; reg valid=0,frame=0,framing_error=0;
 wire signed [3:0] mx,my; wire [2:0] aim; wire linked,restart,accepted;
 integer packets=0;
 control_packet #(.BYTE_TIMEOUT(64),.TIMEOUT_FRAMES(3)) parser(clk,rst_n,data,valid,framing_error,frame,mx,my,aim,linked,restart,accepted);
 always @(posedge clk) if(!rst_n)packets<=0;else if(accepted)packets<=packets+1;
 function [7:0] crc8(input [7:0] c0,input [7:0] value);
 reg[7:0] c;integer i;begin c=c0^value;for(i=0;i<8;i=i+1)c=c[7]?(c<<1)^8'h07:c<<1;crc8=c;end endfunction
 task byte_in(input [7:0] value);begin data=value;valid=1;cycles(1);valid=0;cycles(1);end endtask
 task packet(input [7:0] seq,input [7:0] dx,input [7:0] dy,input [7:0] a,input [7:0] flags,input reg corrupt);
 reg[7:0] c;begin c=crc8(0,seq);c=crc8(c,dx);c=crc8(c,dy);c=crc8(c,a);c=crc8(c,flags);
 byte_in(8'ha5);byte_in(8'h5a);byte_in(seq);byte_in(dx);byte_in(dy);byte_in(a);byte_in(flags);byte_in(c^{7'b0,corrupt});end endtask
 task parser_frame;begin frame=1;cycles(1);frame=0;cycles(1);end endtask

 reg raw_button=0;wire button_level,button_press;integer presses=0;
 fire_button #(.STABLE_CYCLES(4)) button(clk,rst_n,raw_button,button_level,button_press);
 always @(posedge clk)if(!rst_n)presses<=0;else if(button_press)presses<=presses+1;

 reg game_frame=0,game_link=0,fire=0,press=0,game_restart=0;
 reg signed[3:0] dx=0,dy=0;reg[2:0] direction=2;
 wire[7:0] px,ex,bx,score;wire[6:0] py,ey,by;wire bullet,over;wire[2:0] cannon;
 flight_game game(clk,rst_n,game_frame,game_link,dx,dy,direction,fire,press,game_restart,px,ex,bx,py,ey,by,bullet,cannon,score,over);
 task tick;begin game_frame=1;cycles(1);game_frame=0;cycles(1);end endtask
 task game_reset;begin game_restart=1;tick();game_restart=0;end endtask
 reg[57:0] saved;integer i,j,n;reg[6:0] initial_y;
 initial begin
  reset_all();
  // Start glitches shorter than half a bit are ignored; back-to-back bytes preserved.
  rx=0;cycles(1);rx=1;cycles(12);check(rx_count==0,"UART false start");
  serial_byte(8'h00,0);serial_byte(8'hff,0);serial_byte(8'ha5,0);rx=1;cycles(4);
  check(rx_count==3 && last_rx==8'ha5,"UART back-to-back bytes or boundaries");
  serial_byte(8'h55,1);rx=1;cycles(24);check(error_count>0 && rx_count==3,"UART malformed stop");
  serial_byte(8'h39,0);rx=1;cycles(4);check(last_rx==8'h39 && rx_count==4,"UART framing recovery");

  packet(8'hff,8'hfd,3,4,1,0);check(linked && mx==-3 && my==3 && aim==4 && packets==1,"packet signed/range/atomic");
  byte_in(8'ha5);byte_in(8'h5a);byte_in(0);byte_in(1);check(mx==-3,"partial packet leaked");
  cycles(70);packet(0,1,8'hff,2,1,0);check(mx==1 && my==-1 && packets==2,"timeout header recovery or sequence wrap");
  packet(1,2,2,1,1,1);check(mx==1 && packets==2,"CRC corruption accepted");
  packet(1,4,0,2,1,0);packet(1,0,0,5,1,0);packet(1,0,0,2,5,0);
  check(packets==2,"out of range or reserved flags accepted");
  packet(0,3,3,0,1,0);check(mx==1 && packets==2,"duplicate sequence accepted");
  parser_frame();parser_frame();check(linked,"watchdog early");
  packet(0,0,0,2,1,0);parser_frame();check(!linked && mx==0 && my==0,"duplicate refreshed watchdog");
  packet(1,0,0,2,1,0);check(linked,"reconnect packet failed");
  packet(2,0,0,2,0,0);check(!linked,"explicit invalid controls not immediate");
  byte_in(8'ha5);byte_in(8'h5a);byte_in(3);framing_error=1;cycles(1);framing_error=0;
  packet(3,8'h80,0,2,1,0);check(!linked,"signed boundary invalid accepted");
  packet(3,0,0,2,1,0);check(linked,"framing error recovery failed");

  raw_button=1;cycles(2);raw_button=0;cycles(8);check(!button_level && presses==0,"button bounce");
  raw_button=1;cycles(10);check(button_level && presses==1,"debounced press");
  cycles(20);check(presses==1,"held button repeated press event");
  raw_button=0;cycles(10);check(!button_level,"debounced release");

  check(px==24 && py==60 && score==0 && !bullet && !over,"game deterministic reset");
  saved={px,ex,bx,py,ey,by,bullet,cannon,score,over};dx=3;dy=3;fire=1;
  repeat(5)tick();check(saved=={px,ex,bx,py,ey,by,bullet,cannon,score,over},"disconnect did not freeze game");
  game_link=1;fire=0;repeat(60)tick();check(px==151 && py==111,"positive flight clamp");
  game_reset();dx=-3;dy=-3;repeat(60)tick();check(px==8 && py==8,"negative flight clamp");
  dx=0;dy=0;
  for(j=0;j<5;j=j+1)begin
   game_reset();direction=j[2:0];tick();check(cannon==j[2:0],"cannon direction clamp/table");
   fire=1;tick();fire=0;initial_y=by;check(bullet,"physical fire did not create projectile");
   direction=2;tick();
   case(j) 0:check(by==initial_y-2,"bullet dir0");1:check(by==initial_y-1,"bullet dir1");2:check(by==initial_y,"bullet dir2");3:check(by==initial_y+1,"bullet dir3");4:check(by==initial_y+2,"bullet dir4");endcase
   game.bullet_active=0;fire=1;tick();check(!bullet,"fire cooldown too short");fire=0;
  end
  game_reset();direction=2;dy=-3;repeat(10)tick();dy=0;fire=1;tick();fire=0;
  n=0;while(score==0 && n<60)begin tick();n=n+1;end
  check(score==1 && !over,"natural projectile hit and score");
  // Boundary cases preload state in the isolated unit DUT; no synthesis/test hooks in RTL.
  game.score_bcd=8'h98;game.bullet_active=1;game.bullet_x=ex;game.bullet_y=ey;tick();check(score==8'h99,"score99 boundary");
  game.bullet_active=1;game.bullet_x=ex;game.bullet_y=ey;tick();check(score==8'h99,"score overflow");
  game_reset();dy=-3;repeat(10)tick();dy=0;n=0;
  while(!over && n<160)begin tick();n=n+1;end
  check(over,"natural enemy/player collision");
  fire=1;repeat(3)tick();check(over,"held fire auto-restarted");press=1;tick();press=0;fire=0;
  check(!over && px==24 && py==60 && score==0 && !bullet,"physical restart state");
  $display("PASS: UART, packet atomicity/recovery/watchdog, bounce, gameplay/bounds/directions/hits/score/restart");
  $finish;
 end
 initial begin #1000000;$fatal(1,"unit test hung");end
endmodule
