/*
 * Copyright (c) 2026 Zarina and RTU Chipathon contributors
 * SPDX-License-Identifier: Apache-2.0
 */
`default_nettype none
module tt_um_zarina_phone_flight (
    input wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input wire ena, input wire clk, input wire rst_n
);
    wire run_reset_n = rst_n && ena;
    wire [9:0] scan_x, scan_y;
    wire active, hsync, vsync, frame_tick;
    vga_timing timing (.clk(clk),.rst_n(run_reset_n),.x(scan_x),.y(scan_y),
        .active(active),.hsync(hsync),.vsync(vsync),.frame_tick(frame_tick));
    wire [7:0] received;
    wire byte_valid, framing_error;
    uart_rx receiver (.clk(clk),.rst_n(run_reset_n),.rx(ui_in[3]),
        .data(received),.valid(byte_valid),.framing_error(framing_error));
    wire signed [3:0] move_x, move_y;
    wire [2:0] aim;
    wire link_valid, restart, packet_strobe;
    control_packet controls (.clk(clk),.rst_n(run_reset_n),.data(received),.valid(byte_valid),
        .framing_error(framing_error),.frame_tick(frame_tick),.move_x(move_x),.move_y(move_y),
        .aim(aim),.link_valid(link_valid),.restart(restart),.packet_strobe(packet_strobe));
    wire fire_level, fire_press;
    fire_button button (.clk(clk),.rst_n(run_reset_n),.raw_button(ui_in[0]),.level(fire_level),.press(fire_press));
    reg fire_pending, restart_pending;
    always @(posedge clk) begin
        if (!run_reset_n) begin fire_pending <= 0; restart_pending <= 0; end
        else begin
            if (frame_tick || !link_valid) begin fire_pending <= 0; restart_pending <= 0; end
            if (fire_press && link_valid) fire_pending <= 1;
            if (restart) restart_pending <= 1;
        end
    end
    wire [7:0] player_x, enemy_x, bullet_x, score_bcd;
    wire [6:0] player_y, enemy_y, bullet_y;
    wire bullet_active, game_over;
    wire [2:0] cannon_dir;
    flight_game game (.clk(clk),.rst_n(run_reset_n),.frame_tick(frame_tick),.link_valid(link_valid),
        .move_x(move_x),.move_y(move_y),.aim(aim),.fire_level(fire_level),
        .fire_press(fire_pending || fire_press),.restart(restart_pending || restart),
        .player_x(player_x),.player_y(player_y),.enemy_x(enemy_x),.enemy_y(enemy_y),
        .bullet_x(bullet_x),.bullet_y(bullet_y),.bullet_active(bullet_active),
        .cannon_dir(cannon_dir),.score_bcd(score_bcd),.game_over(game_over));
    wire [1:0] red, green, blue;
    pixel_renderer pixels (.pixel_x(scan_x[9:2]),.pixel_y(scan_y[8:2]),
        .player_x(player_x),.player_y(player_y),.enemy_x(enemy_x),.enemy_y(enemy_y),
        .bullet_x(bullet_x),.bullet_y(bullet_y),.bullet_active(bullet_active),
        .cannon_dir(cannon_dir),.score_bcd(score_bcd),.game_over(game_over),.link_valid(link_valid),
        .red(red),.green(green),.blue(blue));
    assign uo_out = !run_reset_n ? 8'h88 : {
        hsync, active && blue[0], active && green[0], active && red[0],
        vsync, active && blue[1], active && green[1], active && red[1]};
    assign uio_out = 8'h00;
    assign uio_oe = 8'h00;
    wire _unused = &{uio_in,ui_in[7:4],ui_in[2:1],packet_strobe,scan_x[1:0],scan_y[9],scan_y[1:0],1'b0};
endmodule
`default_nettype wire
