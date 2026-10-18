// SPDX-License-Identifier: Apache-2.0
// RTU phone flight game. State changes only at vertical blank.
module flight_game (
 input wire clk, rst_n, frame_tick, link_valid,
 input wire signed [3:0] move_x, move_y,
 input wire [2:0] aim,
 input wire fire_level, fire_press, restart,
 output reg [7:0] player_x, enemy_x, bullet_x,
 output reg [6:0] player_y, enemy_y, bullet_y,
 output reg bullet_active,
 output reg [2:0] cannon_dir,
 output reg [7:0] score_bcd,
 output reg game_over
);
 reg [7:0] random_state;
 reg [2:0] cooldown;
 reg [2:0] bullet_dir;
 wire signed [8:0] next_x = $signed({1'b0,player_x}) + {{5{move_x[3]}},move_x};
 wire signed [8:0] next_y = $signed({2'b0,player_y}) + {{5{move_y[3]}},move_y};
 wire [7:0] player_enemy_dx = player_x > enemy_x ? player_x-enemy_x : enemy_x-player_x;
 wire [6:0] player_enemy_dy = player_y > enemy_y ? player_y-enemy_y : enemy_y-player_y;
 wire [7:0] bullet_enemy_dx = bullet_x > enemy_x ? bullet_x-enemy_x : enemy_x-bullet_x;
 wire [6:0] bullet_enemy_dy = bullet_y > enemy_y ? bullet_y-enemy_y : enemy_y-bullet_y;
 wire hit = bullet_active && bullet_enemy_dx <= 8'd7 && bullet_enemy_dy <= 7'd4;
 wire crash = player_enemy_dx <= 8'd10 && player_enemy_dy <= 7'd6;
 wire [6:0] spawn_y = 7'd16 + {1'b0,random_state[5:0]};
 always @(posedge clk) begin
  if (!rst_n) begin
   player_x<=8'd24; player_y<=7'd60; enemy_x<=8'd152; enemy_y<=7'd30;
   bullet_x<=0; bullet_y<=0; bullet_active<=0; cannon_dir<=3'd2;
   score_bcd<=0; game_over<=0; cooldown<=0; bullet_dir<=3'd2; random_state<=8'hA7;
  end else if (frame_tick) begin
   if (restart || (game_over && link_valid && fire_press)) begin
    player_x<=8'd24; player_y<=7'd60; enemy_x<=8'd152; enemy_y<=7'd30;
    bullet_x<=0; bullet_y<=0; bullet_active<=0; cannon_dir<=3'd2;
    score_bcd<=0; game_over<=0; cooldown<=0; bullet_dir<=3'd2; random_state<=8'hA7;
   end else if (link_valid && !game_over) begin
    cannon_dir <= aim <= 3'd4 ? aim : 3'd2;
    if(next_x < 9'sd8) player_x<=8'd8;
    else if(next_x > 9'sd151) player_x<=8'd151;
    else player_x<=next_x[7:0];
    if(next_y < 9'sd8) player_y<=7'd8;
    else if(next_y > 9'sd111) player_y<=7'd111;
    else player_y<=next_y[6:0];
    if(cooldown != 0) cooldown<=cooldown-3'd1;
    if(enemy_x <= 8'd7 || hit) begin
     enemy_x<=8'd152; enemy_y<=spawn_y;
     random_state<={random_state[6:0],random_state[7]^random_state[5]^random_state[4]^random_state[3]};
    end else enemy_x<=enemy_x-8'd1;
    if(bullet_active) begin
     if(hit || bullet_x >= 8'd156 || bullet_y <= 7'd2 || bullet_y >= 7'd117) bullet_active<=0;
     else begin
      bullet_x<=bullet_x+8'd3;
      case(bullet_dir)
       0: bullet_y<=bullet_y-7'd2;
       1: bullet_y<=bullet_y-7'd1;
       3: bullet_y<=bullet_y+7'd1;
       4: bullet_y<=bullet_y+7'd2;
       default: bullet_y<=bullet_y;
      endcase
     end
    end else if(fire_level && cooldown==0) begin
     bullet_x<=player_x+8'd6; bullet_y<=player_y;
     bullet_active<=1; cooldown<=3'd5; bullet_dir<=aim <= 3'd4 ? aim : 3'd2;
    end
    if(hit && score_bcd != 8'h99) begin
     if(score_bcd[3:0] == 4'd9) begin
      score_bcd[3:0]<=0; score_bcd[7:4]<=score_bcd[7:4]+4'd1;
     end else score_bcd[3:0]<=score_bcd[3:0]+4'd1;
    end
    if(crash) begin game_over<=1; bullet_active<=0; end
   end
  end
 end
endmodule
