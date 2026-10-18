/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module vga_timing (
    input wire clk, input wire rst_n,
    output reg [9:0] x, output reg [9:0] y,
    output wire active, output wire hsync, output wire vsync, output wire frame_tick
);
    always @(posedge clk) begin
        if (!rst_n) begin x <= 0; y <= 0; end
        else if (x == 799) begin
            x <= 0;
            if (y == 524) y <= 0;
            else y <= y + 1'b1;
        end else x <= x + 1'b1;
    end
    assign active = x < 640 && y < 480;
    assign hsync = !(x >= 656 && x < 752);
    assign vsync = !(y >= 490 && y < 492);
    assign frame_tick = x == 0 && y == 480;
endmodule
`default_nettype wire
