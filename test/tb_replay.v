`timescale 1ns/1ps
module tb_replay;
 parameter integer BIT_CYCLES=8;
 parameter integer PACKET_COUNT=371;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;reg rx=1;
 wire[7:0] data;wire valid,error;
 wire signed[3:0] mx,my;wire[2:0] aim;wire link,restart,strobe;
 uart_rx #(.CLKS_PER_BIT(BIT_CYCLES)) receiver(clk,rst_n,rx,data,valid,error);
 control_packet #(.BYTE_TIMEOUT(BIT_CYCLES*40)) controls(clk,rst_n,data,valid,error,1'b0,mx,my,aim,link,restart,strobe);
 reg[7:0] memory[0:PACKET_COUNT*8-1];integer i,j,k,count=0;
 always @(posedge clk) if(!rst_n)count<=0;else if(strobe)count<=count+1;
 task cycles(input integer n);repeat(n)@(negedge clk);endtask
 task send_byte(input[7:0] value);integer b;begin
  rx=0;cycles(BIT_CYCLES);for(b=0;b<8;b=b+1)begin rx=value[b];cycles(BIT_CYCLES);end rx=1;cycles(BIT_CYCLES);
 end endtask
 initial begin
  $readmemh("test/output/replay.mem",memory);
  cycles(4);rst_n=1;cycles(4);
  for(i=0;i<PACKET_COUNT;i=i+1)begin
   for(j=0;j<8;j=j+1)send_byte(memory[i*8+j]);
   cycles(4);
   if(count!=i+1)$fatal(1,"replay packet %d not accepted",i);
   if(link!==memory[i*8+6][0] || aim!==memory[i*8+5][2:0])$fatal(1,"replay valid/aim mismatch %d",i);
   if(link && (mx!==memory[i*8+3][3:0] || my!==memory[i*8+4][3:0]))$fatal(1,"replay signed controls mismatch %d",i);
   if(!link && (mx!=0 || my!=0))$fatal(1,"invalid packet movement %d",i);
  end
  $display("PASS: %d control UART packets through receiver+parser, divider %d",PACKET_COUNT,BIT_CYCLES);$finish;
 end
endmodule
