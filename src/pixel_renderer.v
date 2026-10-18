// SPDX-License-Identifier: Apache-2.0
// Combinational procedural graphics on the 160 x 120 logical grid.
module pixel_renderer (
 input wire [7:0] pixel_x, player_x, enemy_x, bullet_x,
 input wire [6:0] pixel_y, player_y, enemy_y, bullet_y,
 input wire bullet_active,
 input wire [2:0] cannon_dir,
 input wire [7:0] score_bcd,
 input wire game_over, link_valid,
 output reg [1:0] red, green, blue
);
 wire [7:0] px = pixel_x>player_x ? pixel_x-player_x : player_x-pixel_x;
 wire [6:0] py = pixel_y>player_y ? pixel_y-player_y : player_y-pixel_y;
 wire [7:0] ex = pixel_x>enemy_x ? pixel_x-enemy_x : enemy_x-pixel_x;
 wire [6:0] ey = pixel_y>enemy_y ? pixel_y-enemy_y : enemy_y-pixel_y;
 wire player_shape = (px<=8'd5 && py<=7'd1) || (px<=8'd1 && py<=7'd4) || (pixel_x+8'd4==player_x && py<=7'd3);
 wire enemy_shape = (ex<=8'd5 && ey<=7'd1) || (ex<=8'd1 && ey<=7'd4) || (pixel_x==enemy_x+8'd4 && ey<=7'd3);
 wire [7:0] cannon_x = pixel_x-player_x;
 reg cannon_shape;
 always @* begin
  cannon_shape=0;
  if(pixel_x>=player_x && cannon_x>=8'd4 && cannon_x<=8'd9) begin
   case(cannon_dir)
    0: cannon_shape = pixel_y + {4'd0,cannon_x[3:1]} == player_y;
    1: cannon_shape = pixel_y + {5'd0,cannon_x[3:2]} == player_y;
    3: cannon_shape = pixel_y == player_y + {5'd0,cannon_x[3:2]};
    4: cannon_shape = pixel_y == player_y + {4'd0,cannon_x[3:1]};
    default: cannon_shape = pixel_y==player_y;
   endcase
  end
 end
 function [14:0] glyph;
  input [3:0] digit;
  begin
   case(digit)
    0:glyph=15'b111_101_101_101_111;
    1:glyph=15'b010_110_010_010_111;
    2:glyph=15'b111_001_111_100_111;
    3:glyph=15'b111_001_111_001_111;
    4:glyph=15'b101_101_111_001_001;
    5:glyph=15'b111_100_111_001_111;
    6:glyph=15'b111_100_111_101_111;
    7:glyph=15'b111_001_010_010_010;
    8:glyph=15'b111_101_111_101_111;
    9:glyph=15'b111_101_111_001_111;
    default:glyph=0;
   endcase
  end
 endfunction
 wire [14:0] tens=glyph(score_bcd[7:4]);
 wire [14:0] ones=glyph(score_bcd[3:0]);
 wire [2:0] score_row=pixel_y[2:0]-3'd3;
 wire [1:0] score_col=pixel_x[1:0];
 // The guards below restrict the valid glyph indices to 0..14.
 wire [3:0] glyph_index=4'd14-({1'b0,score_row}+{score_row,1'b0})-{2'b00,score_col};
 wire score_shape=pixel_y>=7'd3 && pixel_y<=7'd7 &&
   ((pixel_x>=8'd4 && pixel_x<=8'd6 && tens[glyph_index]) ||
    (pixel_x>=8'd8 && pixel_x<=8'd10 && ones[glyph_index]));
 always @* begin
  red=0; green=0; blue=0;
  // Sparse grid-like stars use only bit comparisons, with no stored image.
  if(pixel_x[4:0]==5'd19 && pixel_y[4:0]==5'd13) blue=1;
  if(player_shape) begin green=3; blue=2; end
  if(cannon_shape) begin red=2; green=3; blue=3; end
  if(enemy_shape) begin red=3; green=1; blue=0; end
  if(bullet_active && pixel_y==bullet_y && pixel_x>=bullet_x && pixel_x<=bullet_x+8'd1) begin red=3; green=3; blue=0; end
  if(score_shape) begin red=3; green=3; blue=3; end
  // Top-right lamp: cyan connected, amber stale. Red center cross = game over.
  if(pixel_x>=8'd151 && pixel_x<=8'd155 && pixel_y>=7'd3 && pixel_y<=7'd6) begin
   red=link_valid ? 0 : 3; green=link_valid ? 3 : 1; blue=link_valid ? 3 : 0;
  end
  if(game_over && ((pixel_x>=8'd68 && pixel_x<=8'd92 && pixel_y>=7'd58 && pixel_y<=7'd61) ||
                  (pixel_x>=8'd78 && pixel_x<=8'd81 && pixel_y>=7'd48 && pixel_y<=7'd72))) begin red=3; green=0; blue=0; end
 end
endmodule
