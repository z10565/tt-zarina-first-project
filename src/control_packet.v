/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module control_packet #(
    parameter integer BYTE_TIMEOUT = 8760,
    parameter integer TIMEOUT_FRAMES = 15
) (
    input wire clk, input wire rst_n,
    input wire [7:0] data, input wire valid, input wire framing_error,
    input wire frame_tick,
    output reg signed [3:0] move_x, output reg signed [3:0] move_y,
    output reg [2:0] aim, output reg link_valid,
    output reg restart, output reg packet_strobe
);
    localparam integer TW = $clog2(BYTE_TIMEOUT+1);
    localparam integer FW = $clog2(TIMEOUT_FRAMES+1);
    reg [2:0] state;
    reg [TW-1:0] byte_age;
    reg [FW-1:0] frame_age;
    reg [7:0] crc, seq, px, py, pa, flags, last_sequence;
    reg have_sequence;
    function [7:0] crc_byte;
        input [7:0] previous;
        input [7:0] value;
        reg [7:0] c;
        integer i;
        begin
            c = previous ^ value;
            for (i=0;i<8;i=i+1) c = c[7] ? {c[6:0],1'b0} ^ 8'h07 : {c[6:0],1'b0};
            crc_byte = c;
        end
    endfunction
    wire [7:0] initial_crc = crc_byte(8'h00,data);
    wire [7:0] next_crc = crc_byte(crc,data);
    always @(posedge clk) begin
        if (!rst_n) begin
            state <= 0; byte_age <= 0; frame_age <= 0;
            crc <= 0; seq <= 0; px <= 0; py <= 0; pa <= 2; flags <= 0;
            last_sequence <= 0; have_sequence <= 0;
            move_x <= 0; move_y <= 0; aim <= 2; link_valid <= 0;
            restart <= 0; packet_strobe <= 0;
        end else begin
            restart <= 0; packet_strobe <= 0;
            if (frame_tick && link_valid) begin
                if (frame_age == FW'(TIMEOUT_FRAMES-1)) begin
                    link_valid <= 0; move_x <= 0; move_y <= 0;
                end else frame_age <= frame_age + 1'b1;
            end
            if (state != 0 && !valid) begin
                if (byte_age == TW'(BYTE_TIMEOUT-1)) begin state <= 0; byte_age <= 0; end
                else byte_age <= byte_age + 1'b1;
            end
            if (framing_error) begin state <= 0; byte_age <= 0; end
            else if (valid) begin
                byte_age <= 0;
                case (state)
                    0: if (data == 8'ha5) state <= 1;
                    1: if (data == 8'h5a) begin state <= 2; crc <= 0; end
                       else state <= data == 8'ha5 ? 1 : 0;
                    2: begin seq <= data; crc <= initial_crc; state <= 3; end
                    3: begin px <= data; crc <= next_crc; state <= 4; end
                    4: begin py <= data; crc <= next_crc; state <= 5; end
                    5: begin pa <= data; crc <= next_crc; state <= 6; end
                    6: begin flags <= data; crc <= next_crc; state <= 7; end
                    7: begin
                        state <= data == 8'ha5 ? 1 : 0;
                        if (data == crc && pa <= 4 && flags[7:2] == 0 &&
                            $signed(px) >= -8'sd3 && $signed(px) <= 8'sd3 &&
                            $signed(py) >= -8'sd3 && $signed(py) <= 8'sd3 &&
                            (!have_sequence || seq != last_sequence)) begin
                            move_x <= flags[0] ? px[3:0] : 4'd0;
                            move_y <= flags[0] ? py[3:0] : 4'd0;
                            aim <= pa[2:0]; link_valid <= flags[0];
                            restart <= flags[0] && flags[1]; packet_strobe <= 1;
                            last_sequence <= seq; have_sequence <= 1; frame_age <= 0;
                            // A valid CRC byte that happens to equal A5 is not a new header.
                            state <= 0;
                        end
                    end
                    default: state <= 0;
                endcase
            end
        end
    end
endmodule
`default_nettype wire
