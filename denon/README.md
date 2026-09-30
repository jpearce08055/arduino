# Denon receiver configuration reader

`denon_config.py` finds a Denon receiver on the home network and prints its
settings: model, firmware, MAC address, input, volume, sound mode, Audyssey,
channel levels, speaker setup, source names, zones 2 and 3, and video and
system settings. It only sends queries, so it never changes anything.

## Running it

Run it on a computer on the same network as the receiver. It needs Python 3.8
or newer and nothing else.

```
python3 denon_config.py                        # search 192.168.11.0/24
python3 denon_config.py --host 192.168.11.23   # use a known address
python3 denon_config.py --save                 # also save a JSON snapshot
python3 denon_config.py --json                 # print JSON for other programs
```

On Windows, type `py` in place of `python3`. A full read takes about 20 seconds.

## How it reads the receiver

| Interface      | Port                                  | What it provides                                                                    |
| -------------- | ------------------------------------- | ----------------------------------------------------------------------------------- |
| Telnet control | 23                                    | Input, volume, sound mode, Audyssey, channel levels, speakers, sources, zones, video |
| Web API        | 8080 (2016 and later), 80 (older)     | Model, MAC address, API version, main zone status                                   |
| HEOS CLI       | 1255 (HEOS Built-in models)           | Firmware and serial number, network, HEOS playback                                  |

Receivers ignore queries they don't support, so older models just show fewer
settings.

## If something is missing

- **Nothing found:** this computer must be on the receiver's network (its own
  address should start with `192.168.11.`). Switch the receiver on, or set
  **Setup > Network > Network Control** to **Always On** (called Network
  Standby on older models) so it answers while in standby. Or pass `--host`
  with the address from your router's device list.
- **Telnet refused:** the receiver accepts one telnet connection at a time.
  Close other control apps, such as Home Assistant's Denon integration, and run
  it again.
- **Settings missing on an older model:** try `--delay 0.5` to give the
  receiver more time between queries.
