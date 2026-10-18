# Flight game and interface specification

Status: implementation contract. Android records independent TYPE_ACCELEROMETER m/s² (including gravity) and TYPE_GYROSCOPE rad/s with monotonic nanosecond timestamps. v0.3 adds standalone control mapping/USB host CDC while preserving those raw records; v0.2 PC ADB streaming remains available.

## Platform baseline

SKY130, existing ttsky26d action family; official SKY Verilog template migration. Budget at most three tiles; use supported 1x2 (two tiles) unless platform research establishes a supported three-tile shape. Do not use 3x2 (six). Exact event shuttle and physical board are not supplied; organizer confirmation remains a submission blocker.

Single 25,200,000 Hz clock, VGA 640x480 with 800 clocks/line and 525 lines/frame (60 Hz). H active 0..639, front porch 640..655, negative HSYNC 656..751, back porch 752..799. V active 0..479, front porch 480..489, negative VSYNC 490..491, back porch 492..524. RGB black outside active area. Gameplay tick at x=0,y=480: all game state is stable during visible scanout. Logical game grid 160x120, pixels enlarged 4x4.

## Pins

`ui_in[3]` UART RX (idle high, two-flop synchronizer); `ui_in[0]` physical fire (active high with external pulldown; synchronized and debounced). Other ui pins unused. All uio pins inputs: uio_oe=0 and uio_out=0. No TX/feedback. Tiny VGA: uo bits [0,1,2,3,4,5,6,7] = [R1,G1,B1,VSYNC,R0,G0,B0,HSYNC].

## Serial controls v1

115200 baud, 8N1, no flow control. RX divider 219 clocks at 25.2 MHz (~115068 baud, -0.114%). Eight-byte packet: `A5 5A sequence dx dy aim flags crc`.

- sequence unsigned 8-bit rolling; duplicate valid sequence is ignored (does not refresh watchdog); any different sequence accepted, including wrap.
- dx/dy signed two's-complement bytes, range -3..3 logical pixels per frame; aim unsigned 0..4.
- flags bit0 CONTROL_VALID; bit1 RESTART request, applied once per accepted packet; other bits must be zero. A restart is honored only with CONTROL_VALID.
- CRC-8 poly 0x07, init 0, no reflection/xorout, covers sequence/dx/dy/aim/flags. Validate ranges, reserved bits, CRC and UART stop bit before atomic register update.
- Parser abandons partial packet after four UART character times without a byte; resynchronizes on header. A malformed byte/CRC cannot partially update controls.
- Host updates 30 Hz. If valid data stops, after 15 VGA ticks (~250 ms) link is stale. Movement/enemies/projectiles freeze and physical firing is inhibited. New valid packets resume. Invalid-control packet immediately marks link stale. No host fire command exists.

## Preprocessing (Android or PC host)

Standalone: phone preprocessing -> Android USB host CDC -> ETR management relay -> UART ui3. PC alternative: phone -> ADB local TCP JSONL -> PC preprocessing -> ETR USB relay -> UART ui3. Both implement the same control mapping below. No Bluetooth/Wi-Fi/USB peripheral is implemented in silicon. USB-host roles, readiness handshake and reversible startup are documented in [STANDALONE.md](STANDALONE.md); physical compatibility/power remains unverified.

Hold phone approximately face-up and stationary for initial calibration. Host estimates accelerometer neutral and gyroscope bias for one second; resets calibration on a new capture session. Low-pass acceleration, subtract neutral; positive X moves right, positive Y moves up (negative screen dy). Acceleration dead zone 0.6 m/s², saturation 4.5 m/s², quantize to -3..3. Integrate bias-corrected gyro Z with 0.06 rad/s dead zone, clamp relative aim angle to +/-0.65 rad, choose five cannon directions; neutral=2. Bound integration dt and mark controls invalid when either sensor is stale. Bridge docs/tests specify exact quantization and thresholds. Recalibration resets aim neutral. No ML.

## Gameplay

160x120 logical playfield. Player center initially (24,60), clamp x=8..151,y=8..111. One enemy, one player projectile, five right-facing cannon directions. Direction 0..4: projectile dx=3 with dy=-2,-1,0,1,2. Physical held fire repeats no faster than once per six frames, only if projectile slot free and link valid. Release and press fire after game over restarts; restart packet also supported. Reset/restart clears score/projectile/game-over and restores initial plane/enemy state deterministically.

Enemy enters from right and moves left, respawns at bounded pseudo-random y; deterministic seeded LFSR. Axis-aligned compact hitboxes; a projectile/enemy hit removes projectile, respawns enemy, increments displayed two-digit BCD score up to 99. Player/enemy collision sets game over and freezes gameplay. Procedural plane silhouettes, cannon, projectiles, score glyphs, and connection/game-over indicators; no framebuffer.

RTL module interface: `flight_game(clk,rst_n,frame_tick,link_valid, signed [3:0] move_x,move_y,[2:0] aim,fire_level,fire_press,restart, [7:0] player_x,enemy_x,bullet_x,[6:0] player_y,enemy_y,bullet_y,bullet_active,[2:0] cannon_dir,[7:0] score_bcd,game_over)`. Enemy is always present. All state updates only on frame_tick. Renderer takes these state ports plus [7:0] pixel_x,[6:0] pixel_y,link_valid, outputs [1:0] red,green,blue. Game over fire_press must be remembered until frame_tick by the root top-level.
