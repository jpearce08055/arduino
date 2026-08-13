# Arduino files for GCARC projects

Sketches and small programs for Gloucester County Amateur Radio Club (W2MMD) work.

## Grok Compass

A short browser game to help you and a student decide whether they should use Grok.

Open `grok-check/index.html` in a browser (double-click the file, or from this folder run `python3 -m http.server` and visit `/grok-check/`).

The student plays seven school situations and picks what they would actually do. At the end you get one of five recommendations:

- **Yes — as a tutor, not a ghostwriter**
- **Yes, with ground rules**
- **They don't need it — it is optional**
- **Not yet — too easy to skip the thinking**
- **No — honesty first**

The result screen includes a short note for the adult. This is a conversation starter, not a diagnosis. If a class forbids AI, follow that rule.

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
