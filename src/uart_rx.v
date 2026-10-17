/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module uart_rx #(
    parameter integer CLKS_PER_BIT = 219
) (
    input wire clk, input wire rst_n, input wire rx,
    output reg [7:0] data, output reg valid, output reg framing_error
);
    localparam integer W = $clog2(CLKS_PER_BIT);
    reg [1:0] rx_sync;
    reg [1:0] state;
    reg [W-1:0] timer;
    reg [2:0] bit_index;
    reg [7:0] shift;
    always @(posedge clk) begin
        if (!rst_n) begin
            rx_sync <= 2'b11; state <= 0; timer <= 0;
            bit_index <= 0; shift <= 0; data <= 0;
            valid <= 0; framing_error <= 0;
        end else begin
            rx_sync <= {rx_sync[0],rx};
            valid <= 0; framing_error <= 0;
            case (state)
                0: if (!rx_sync[1]) begin state <= 1; timer <= W'(CLKS_PER_BIT/2-1); end
                1: if (timer != 0) timer <= timer - 1'b1;
                   else if (!rx_sync[1]) begin state <= 2; timer <= W'(CLKS_PER_BIT-1); bit_index <= 0; end
                   else state <= 0;
                2: if (timer != 0) timer <= timer - 1'b1;
                   else begin
                       shift[bit_index] <= rx_sync[1];
                       timer <= W'(CLKS_PER_BIT-1);
                       if (bit_index == 7) state <= 3;
                       else bit_index <= bit_index + 1'b1;
                   end
                3: if (timer != 0) timer <= timer - 1'b1;
                   else begin
                       state <= 0;
                       if (rx_sync[1]) begin data <= shift; valid <= 1; end
                       else framing_error <= 1;
                   end
                default: state <= 0;
            endcase
        end
    end
endmodule
`default_nettype wire
