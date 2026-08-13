# Arduino files for GCARC projects

Sketches for Gloucester County Amateur Radio Club (W2MMD) Arduino work.

## CW Practice Keyer

`CW_Practice_Keyer` is a Morse (CW) practice keyer and beacon for an Arduino Uno or compatible board.

### Hardware

| Part | Connection |
| --- | --- |
| Straight key or pushbutton | Pin 2 to GND (internal pull-up) |
| Piezo speaker | Pin 8 to GND |
| Onboard LED | Pin 13 (built-in) shows key-down |

### Use

1. Open `CW_Practice_Keyer/CW_Practice_Keyer.ino` in the Arduino IDE.
2. Select your board and port, then Upload.
3. Open Serial Monitor at **9600 baud**, with newline ending.
4. Close the key to hear sidetone and light the LED.
5. Type `help` for serial commands:

```
wpm 18
msg CQ CQ DE W2MMD K
send
mode auto
mode key
stop
status
```

Change the default callsign in the sketch (or with `msg`) before using this as an on-air beacon.
