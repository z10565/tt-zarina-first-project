/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module fire_button #(
    parameter integer STABLE_CYCLES = 126000
) (
    input wire clk, input wire rst_n, input wire raw_button,
    output reg level, output reg press
);
    localparam integer W = $clog2(STABLE_CYCLES+1);
    reg [1:0] synchronizer;
    reg [W-1:0] stable_count;
    always @(posedge clk) begin
        if (!rst_n) begin synchronizer <= 0; stable_count <= 0; level <= 0; press <= 0; end
        else begin
            synchronizer <= {synchronizer[0],raw_button}; press <= 0;
            if (synchronizer[1] == level) stable_count <= 0;
            else if (stable_count == W'(STABLE_CYCLES-1)) begin
                stable_count <= 0; level <= synchronizer[1]; press <= synchronizer[1];
            end else stable_count <= stable_count + 1'b1;
        end
    end
endmodule
`default_nettype wire
