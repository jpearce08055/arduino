#!/usr/bin/env python3
"""Read the configuration of a Denon receiver on the local network.

Finds the receiver (SSDP discovery, then a sweep of the subnet), then reads its
settings through whichever of these interfaces the model offers:

  Telnet control, port 23      power, input, volume, sound mode, Audyssey,
                               channel levels, speaker setup, source names,
                               zones 2 and 3, video and system settings
  Web API, port 8080 (2016+    model, MAC address, API version,
  models) or 80 (older)        main zone status, source list
  HEOS CLI, port 1255 (HEOS    firmware and serial number, network type,
  Built-in models)             HEOS volume and what's playing

Only queries are sent, so no setting is ever changed.

Examples:
  python3 denon_config.py                         # search 192.168.11.0/24
  python3 denon_config.py --host 192.168.11.23    # skip the search
  python3 denon_config.py --save                  # also write a JSON snapshot
  python3 denon_config.py --json                  # print JSON instead

Needs Python 3.8+ and nothing outside the standard library.
"""

import argparse
import concurrent.futures
import datetime
import ipaddress
import json
import re
import socket
import sys
import textwrap
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

DEFAULT_SUBNET = "192.168.11.0/24"
TELNET_PORT = 23
HEOS_PORT = 1255
HTTP_PORTS = (8080, 80)  # 8080 on 2016 and later models, 80 on earlier ones
HTTP_PAGES = ("Deviceinfo.xml", "formMainZone_MainZoneXml.xml")
SSDP_ADDR = ("239.255.255.250", 1900)
SSDP_TARGETS = (
    "urn:schemas-denon-com:device:ACT-Denon:1",  # HEOS Built-in models
    "urn:schemas-upnp-org:device:MediaRenderer:1",  # older network receivers
)
UPNP_FIELDS = ("friendlyName", "manufacturer", "modelName", "modelNumber", "serialNumber")
BRANDS = {"0": "Denon", "1": "Marantz"}

# Telnet queries as (command, reply prefix, report section, label, format).
# Receivers ignore queries they don't support, so the list errs on the side of
# asking. Each reply is matched to its longest known prefix, so "MVMAX 98" is
# the volume limit, not the volume. A None command marks a reply that arrives
# alongside another one.
TELNET_QUERIES = [
    ("PW?", "PW", "Status", "Power", "text"),
    ("ZM?", "ZM", "Status", "Main zone", "text"),
    ("SI?", "SI", "Status", "Input", "text"),
    ("MV?", "MV", "Status", "Volume", "volume"),
    (None, "MVMAX", "Status", "Volume limit", "volume"),
    ("MU?", "MU", "Status", "Mute", "text"),
    ("MS?", "MS", "Status", "Sound mode", "text"),
    ("MSQUICK ?", "MSQUICK", "Status", "Quick select", "text"),
    ("SD?", "SD", "Status", "Audio input mode", "text"),
    ("DC?", "DC", "Status", "Digital input mode", "text"),
    ("SV?", "SV", "Status", "Video select", "text"),
    ("SSINFAISSIG ?", "SSINFAISSIG", "Status", "Input signal", "text"),
    ("SSINFAISFSV ?", "SSINFAISFSV", "Status", "Input sampling rate", "text"),
    ("SLP?", "SLP", "Status", "Sleep timer", "minutes"),
    ("SPPR ?", "SPPR", "Status", "Speaker preset", "text"),
    ("PSMULTEQ: ?", "PSMULTEQ:", "Room correction", "MultEQ", "text"),
    ("PSDYNEQ ?", "PSDYNEQ", "Room correction", "Dynamic EQ", "text"),
    ("PSREFLEV ?", "PSREFLEV", "Room correction", "Reference level offset", "db"),
    ("PSDYNVOL ?", "PSDYNVOL", "Room correction", "Dynamic Volume", "text"),
    ("PSLFC ?", "PSLFC", "Room correction", "Audyssey LFC", "text"),
    ("PSCNTAMT ?", "PSCNTAMT", "Room correction", "LFC containment amount", "text"),
    ("PSGEQ ?", "PSGEQ", "Room correction", "Graphic EQ", "text"),
    ("PSDIRAC ?", "PSDIRAC", "Room correction", "Dirac Live filter", "text"),
    ("PSTONE CTRL ?", "PSTONE CTRL", "Audio", "Tone control", "text"),
    ("PSBAS ?", "PSBAS", "Audio", "Bass", "level"),
    ("PSTRE ?", "PSTRE", "Audio", "Treble", "level"),
    ("PSDRC ?", "PSDRC", "Audio", "Dynamic compression", "text"),
    ("PSLFE ?", "PSLFE", "Audio", "LFE level", "lfe"),
    ("PSDEL ?", "PSDEL", "Audio", "Audio delay", "ms"),
    ("PSDIL ?", "PSDIL", "Audio", "Dialog level", "level"),
    ("PSSWL ?", "PSSWL", "Audio", "Subwoofer level", "level"),
    ("PSSWR ?", "PSSWR", "Audio", "Subwoofer in Direct/Stereo", "text"),
    ("PSCINEMA EQ. ?", "PSCINEMA EQ.", "Audio", "Cinema EQ", "text"),
    ("PSLOM ?", "PSLOM", "Audio", "Loudness management", "text"),
    ("PSRSTR ?", "PSRSTR", "Audio", "Audio restorer", "text"),
    ("PSDEH ?", "PSDEH", "Audio", "Dialog enhancer", "text"),
    ("PSNEURAL ?", "PSNEURAL", "Audio", "Neural:X", "text"),
    ("PSSPV ?", "PSSPV", "Audio", "Speaker virtualizer", "text"),
    ("PSMODE: ?", "PSMODE:", "Audio", "Surround parameter mode", "text"),
    ("PSEFF ?", "PSEFF", "Audio", "Effect", "text"),
    ("PSFRONT ?", "PSFRONT", "Audio", "Front speakers", "text"),
    ("CV?", "CV", "Channel levels", None, "channels"),
    ("SSSPC ?", "SSSPC", "Speaker setup", "Speaker config", "keyed"),
    ("SSDIS ?", "SSDIS", "Speaker setup", "Distances", "keyed"),
    ("SSLEV ?", "SSLEV", "Speaker setup", "Levels", "keyed"),
    ("SSCFR ?", "SSCFR", "Speaker setup", "Crossovers", "keyed"),
    ("SSPAA ?", "SSPAA", "Speaker setup", "Amp assign", "keyed"),
    ("SSFUN ?", "SSFUN", "Sources", "names", "keyed"),
    ("SSSOD ?", "SSSOD", "Sources", "use", "keyed"),
    ("VSMONI ?", "VSMONI", "Video", "HDMI monitor out", "text"),
    ("VSAUDIO ?", "VSAUDIO", "Video", "HDMI audio output", "text"),
    ("VSVPM ?", "VSVPM", "Video", "Video processing", "text"),
    ("VSSC ?", "VSSC", "Video", "Resolution", "text"),
    ("VSSCH ?", "VSSCH", "Video", "Resolution (HDMI)", "text"),
    ("VSASP ?", "VSASP", "Video", "Aspect ratio", "text"),
    ("VSVST ?", "VSVST", "Video", "Vertical stretch", "text"),
    ("PV?", "PV", "Video", "Picture mode", "text"),
    ("SSHOS ?", "SSHOS", "Video", "HDMI setup", "keyed"),
    ("NSFRN ?", "NSFRN", "System", "Friendly name", "text"),
    ("SSINFFRM ?", "SSINFFRM", "System", "Firmware", "keyed"),
    ("STBY?", "STBY", "System", "Auto standby", "text"),
    ("ECO?", "ECO", "System", "ECO mode", "text"),
    ("DIM ?", "DIM", "System", "Display dimmer", "text"),
    ("BTTX ?", "BTTX", "System", "Bluetooth transmitter", "text"),
    ("SSVCTZMA ?", "SSVCTZMA", "System", "Volume settings", "keyed"),
    ("SSLOC ?", "SSLOC", "System", "Setup lock", "text"),
]
# The same queries for zones 2 and 3, prefixed with Z2 / Z3.
ZONE_QUERIES = [
    ("?", "", None, "zone"),
    ("MU?", "MU", "Mute", "text"),
    ("CV?", "CV", "Channel levels", "channels"),
    ("PSBAS ?", "PSBAS", "Bass", "level"),
    ("PSTRE ?", "PSTRE", "Treble", "level"),
    ("HPF?", "HPF", "High-pass filter", "text"),
    ("CS?", "CS", "Stereo/mono", "text"),
    ("SLP?", "SLP", "Sleep timer", "minutes"),
    ("STBY?", "STBY", "Auto standby", "text"),
]
TELNET_QUERIES += [
    (f"Z{zone}{command}", f"Z{zone}{prefix}", f"Zone {zone}", label, kind)
    for zone in "23"
    for command, prefix, label, kind in ZONE_QUERIES
]
SECTION_ORDER = (
    "Status", "Room correction", "Audio", "Channel levels", "Speaker setup",
    "Sources", "Zone 2", "Zone 3", "Video", "System",
)
CHANNELS = {
    "FL": "front left", "FR": "front right", "C": "center",
    "SW": "subwoofer", "SW2": "subwoofer 2", "SW3": "subwoofer 3", "SW4": "subwoofer 4",
    "SL": "surround left", "SR": "surround right",
    "SBL": "surround back left", "SBR": "surround back right", "SB": "surround back",
    "FHL": "front height left", "FHR": "front height right",
    "FWL": "front wide left", "FWR": "front wide right",
    "TFL": "top front left", "TFR": "top front right",
    "TML": "top middle left", "TMR": "top middle right",
    "TRL": "top rear left", "TRR": "top rear right",
    "RHL": "rear height left", "RHR": "rear height right",
    "FDL": "front Dolby left", "FDR": "front Dolby right",
    "SDL": "surround Dolby left", "SDR": "surround Dolby right",
    "BDL": "back Dolby left", "BDR": "back Dolby right",
    "SHL": "surround height left", "SHR": "surround height right",
    "TS": "top surround", "CH": "center height",
}
SPEAKER_SIZES = {"LAR": "large", "SMA": "small", "NON": "none"}
WEB_STATUS = (
    ("Power", "Power"),
    ("Main zone", "ZonePower"),
    ("Input", "InputFuncSelect"),
    ("Sound mode", "selectSurround"),
    ("Volume", "MasterVolume"),
    ("Mute", "Mute"),
    ("ECO mode", "ECOMode"),
)
NOT_FOUND_HELP = """\
No Denon receiver found on {subnet}.
  - This computer must be on that network (its own address should be in {subnet}).
  - Switch the receiver on, or set Setup > Network > Network Control to
    "Always On" ("Network Standby" on older models) so it answers in standby.
  - If you know its address (your router's device list shows it), run:
      python3 denon_config.py --host <address>"""

_BY_PREFIX = sorted(TELNET_QUERIES, key=lambda query: len(query[1]), reverse=True)
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never proxy LAN requests


def log(message):
    print(message, file=sys.stderr, flush=True)


def http_get(url, timeout=4):
    with _OPENER.open(url, timeout=timeout) as response:
        return response.read()


def port_open(ip, port, timeout=0.5):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def describe_error(exc):
    if isinstance(exc, ConnectionRefusedError):
        return "connection refused"
    if isinstance(exc, socket.timeout):
        return "no answer (timed out)"
    return str(exc) or type(exc).__name__


# --- Finding the receiver ----------------------------------------------------


def ssdp_search(wait=3.0):
    """Return {ip: [description URLs]} for UPnP devices that answer an M-SEARCH."""
    found = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(0.3)
        try:
            for target in SSDP_TARGETS:
                request = (
                    "M-SEARCH * HTTP/1.1\r\n"
                    f"HOST: {SSDP_ADDR[0]}:{SSDP_ADDR[1]}\r\n"
                    'MAN: "ssdp:discover"\r\n'
                    "MX: 2\r\n"
                    f"ST: {target}\r\n\r\n"
                )
                sock.sendto(request.encode("ascii"), SSDP_ADDR)
        except OSError:
            return found  # no multicast route; the subnet sweep covers this
        end = time.monotonic() + wait
        while time.monotonic() < end:
            try:
                data, (ip, _port) = sock.recvfrom(8192)
            except (socket.timeout, ConnectionResetError):  # Windows reports stray ICMP as a reset
                continue
            except OSError:
                break
            match = re.search(rb"^location:\s*(\S+)", data, re.IGNORECASE | re.MULTILINE)
            if match:
                urls = found.setdefault(ip, [])
                url = match.group(1).decode("ascii", "replace")
                if url not in urls:
                    urls.append(url)
    return found


def upnp_info(url):
    """friendlyName, manufacturer, modelName etc. from a UPnP device description."""
    root = ET.fromstring(http_get(url, timeout=3))
    info = {}
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]  # drop the XML namespace
        text = (element.text or "").strip()
        if tag in UPNP_FIELDS and text and tag not in info:
            info[tag] = text
    return info


def denon_upnp_info(urls):
    """UPnP info from the first description naming Denon, Marantz or HEOS, else None."""
    for url in urls:
        try:
            info = upnp_info(url)
        except Exception:
            continue
        if re.search(r"denon|marantz|heos", " ".join(info.values()), re.IGNORECASE):
            info["found_by"] = "SSDP"
            return info
    return None


def identify(ip):
    """A short description if ip answers like a Denon or Marantz device, else None."""
    try:
        for port in HTTP_PORTS:
            if not port_open(ip, port):
                continue
            for page in HTTP_PAGES:
                try:
                    values, _lists = parse_page(http_get(f"http://{ip}:{port}/goform/{page}", timeout=3))
                except Exception:
                    continue
                name = (
                    values.get("ManualModelName")
                    or values.get("ModelName", "").lstrip("*")
                    or values.get("FriendlyName")
                )
                if name:
                    return name
        if port_open(ip, HEOS_PORT):
            return "HEOS device"
        with socket.create_connection((ip, TELNET_PORT), timeout=0.5) as sock:
            sock.sendall(b"PW?\r")
            sock.settimeout(1.5)
            if re.search(rb"PW(ON|STANDBY)", sock.recv(256)):
                return "Denon receiver"
    except Exception:
        pass
    return None


def discover(subnet):
    """Find Denon devices: {ip: discovery info}. SSDP first, then a subnet sweep."""
    log("Searching for Denon devices (SSDP)...")
    replies = ssdp_search()
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        infos = dict(zip(replies, pool.map(denon_upnp_info, replies.values())))
    found = {ip: info for ip, info in infos.items() if info}
    if found:
        return found
    hosts = [str(host) for host in subnet.hosts()] or [str(subnet.network_address)]
    log(f"No Denon device answered SSDP; checking the {len(hosts)} addresses in {subnet} (about 10 seconds)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        for ip, label in zip(hosts, pool.map(identify, hosts)):
            if label:
                found[ip] = {"found_by": "subnet sweep", "looks_like": label}
    return found


# --- Reading it --------------------------------------------------------------


def _line_text(raw):
    raw = raw.strip(b"\r\n\x00 ")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _connect(ip, port, attempts=3):
    """Connect, retrying briefly: the receiver may still be closing a previous session."""
    for attempt in range(attempts):
        try:
            return socket.create_connection((ip, port), timeout=5)
        except ConnectionRefusedError:
            if attempt == attempts - 1:
                raise
            time.sleep(1)


def telnet_read(ip, delay):
    """Send every telnet query and return the receiver's reply lines."""
    commands = list(dict.fromkeys(query[0] for query in TELNET_QUERIES if query[0]))
    lines = []
    buffer = b""
    sock = _connect(ip, TELNET_PORT)

    def collect(seconds):
        nonlocal buffer
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                raise EOFError
            *done, buffer = (buffer + chunk).split(b"\r")
            lines.extend(_line_text(line) for line in done if line.strip())

    with sock:
        sock.settimeout(0.05)
        try:
            for command in commands:
                sock.sendall(command.encode("ascii") + b"\r")
                collect(delay)
            collect(1.5)
        except (EOFError, ConnectionResetError, BrokenPipeError):
            if not lines:
                raise ConnectionError("the receiver closed the connection") from None
    return lines


def parse_page(raw):
    """Flatten a Denon XML page into ({tag: text}, {tag: [texts]})."""
    values, lists = {}, {}
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return values, lists
    for child in root:
        items = [element for element in child if element.tag == "value"]
        if len(child) == 0:
            values[child.tag] = (child.text or "").strip()
        elif len(items) == len(child) == 1:
            values[child.tag] = "".join(items[0].itertext()).strip()
        elif items and len(items) == len(child):
            lists[child.tag] = ["".join(item.itertext()).strip() for item in items]
    return values, lists


def http_read(ip):
    """Fetch the device info and main zone pages from whichever web port answers."""
    for port in HTTP_PORTS:
        if not port_open(ip, port, timeout=2):
            continue
        pages = {}
        for page in HTTP_PAGES:
            try:
                raw = http_get(f"http://{ip}:{port}/goform/{page}")
            except Exception:
                continue
            values, lists = parse_page(raw)
            pages[page] = {"values": values, "lists": lists, "xml": raw.decode("utf-8", "replace")}
        if pages:
            return {"port": port, "pages": pages}
    raise ConnectionError(f"no web API on port {' or '.join(map(str, HTTP_PORTS))}")


def heos_read(ip):
    """Ask the HEOS CLI for its player list and this player's state."""
    with _connect(ip, HEOS_PORT) as sock, sock.makefile("rb") as reader:

        def ask(command):
            sock.sendall(f"heos://{command}\r\n".encode())
            name = command.split("?", 1)[0]
            while True:
                line = reader.readline()
                if not line:
                    raise ConnectionError("HEOS closed the connection")
                reply = json.loads(line)
                heos = reply.get("heos", {})
                if heos.get("command") == name and "under process" not in heos.get("message", ""):
                    return reply

        players = ask("player/get_players").get("payload") or []
        data = {"players": players}
        me = next((player for player in players if player.get("ip") == ip), None)
        if me:
            pid = me.get("pid")
            for what in ("get_volume", "get_mute", "get_play_state", "get_play_mode"):
                message = ask(f"player/{what}?pid={pid}").get("heos", {}).get("message", "")
                data[what] = dict(urllib.parse.parse_qsl(message))
            data["now_playing"] = ask(f"player/get_now_playing_media?pid={pid}").get("payload") or {}
        return data


def read_device(ip, discovery, delay):
    """Read everything the device offers; return the raw data plus a report."""
    result = {
        "host": ip,
        "read_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "discovery": discovery,
        "telnet": None,
        "http": None,
        "heos": None,
        "errors": {},
    }
    telnet_seconds = len({query[0] for query in TELNET_QUERIES if query[0]}) * delay + 1.5
    readers = (
        ("telnet", f"telnet control, about {telnet_seconds:.0f} s", lambda: telnet_read(ip, delay)),
        ("http", "web API", lambda: http_read(ip)),
        ("heos", "HEOS CLI", lambda: heos_read(ip)),
    )
    for key, name, read in readers:
        log(f"{ip}: reading {name}...")
        try:
            result[key] = read()
        except Exception as exc:  # note what failed and carry on with the others
            result["errors"][key] = describe_error(exc)
    result["report"] = build_report(result)
    return result


# --- Making sense of it ------------------------------------------------------


def _number(value):
    """'45' -> 45.0 and '455' -> 45.5: a third digit is tenths (half steps)."""
    if not value.isdigit() or not 1 <= len(value) <= 3:
        return None
    if len(value) == 3:
        return int(value[:2]) + int(value[2]) / 10
    return float(value)


def fmt_volume(value):
    """Master and zone volume: 80 is 0 dB and 99 means minimum."""
    number = _number(value)
    if number is None:
        return value
    if number >= 99:
        return "minimum (---)"
    return f"{number:g} ({number - 80:+g} dB)"


def fmt_level(value):
    """Channel levels, bass, treble and similar: 50 is 0 dB."""
    number = _number(value)
    return value if number is None else f"{number - 50:+g} dB"


FORMATS = {
    "text": lambda value: value,
    "volume": fmt_volume,
    "level": fmt_level,
    "db": lambda value: f"{value} dB" if value.isdigit() else value,
    "lfe": lambda value: f"{-int(value)} dB" if value.isdigit() else value,
    "ms": lambda value: f"{int(value)} ms" if value.isdigit() else value,
    "minutes": lambda value: f"{int(value)} min" if value.isdigit() else value,
}


def _add(items, label, value):
    """Store a value; a second, different reply for the same label is appended."""
    if not value:
        return
    old = items.get(label)
    if old is None:
        items[label] = value
    elif value not in old.split(", "):
        items[label] = f"{old}, {value}"


def merge_sources(names, use):
    """{input: displayed name} from the rename and source-delete tables."""
    merged = {}
    for key in list(names) + [key for key in use if key not in names]:
        name = names.get(key) or key
        state = use.get(key, "USE")
        if state == "USE":
            merged[key] = name
        else:
            merged[key] = f"{name}  ({'hidden' if state == 'DEL' else state})"
    return merged


def decode_telnet(lines):
    """Sort telnet replies into report sections; return (sections, unknown lines)."""
    sections, unknown = {}, []
    for line in lines:
        query = next((query for query in _BY_PREFIX if line.startswith(query[1])), None)
        if query is None:
            if line not in unknown:
                unknown.append(line)
            continue
        _command, prefix, section, label, kind = query
        value = line[len(prefix):].strip()
        items = sections.setdefault(section, {})
        if kind in ("channels", "keyed"):
            key, _, val = value.partition(" ")
            if not key or key == "END":
                continue
            if kind == "channels":
                key = f"{key} ({CHANNELS[key]})" if key in CHANNELS else key
                val = fmt_level(val)
            elif prefix == "SSSPC":
                val = SPEAKER_SIZES.get(val, val)
            target = items if label is None else items.setdefault(label, {})
            target[key] = val.strip()
        elif kind == "zone":
            if value in ("ON", "OFF"):
                _add(items, "Power", value)
            elif value.isdigit():
                _add(items, "Volume", fmt_volume(value))
            else:
                _add(items, "Input", value)
        else:
            _add(items, label, FORMATS[kind](value))
    if "Sources" in sections:
        tables = sections["Sources"]
        sections["Sources"] = merge_sources(tables.get("names", {}), tables.get("use", {}))
    return sections, unknown


def _web_status(values):
    status = {}
    for label, tag in WEB_STATUS:
        value = values.get(tag)
        if not value:
            continue
        if tag == "MasterVolume":
            try:
                value = f"{float(value):g} dB"
            except ValueError:
                pass
        status[label] = value
    return status


def _web_sources(lists):
    inputs = lists.get("InputFuncList", [])
    names = dict(zip(inputs, lists.get("RenameSource", [])))
    use = dict(zip(inputs, lists.get("SourceDelete", [])))
    return merge_sources({key: names.get(key, "") for key in inputs}, use)


def _mac(value):
    if value and re.fullmatch(r"[0-9A-Fa-f]{12}", value):
        return ":".join(value[i:i + 2] for i in range(0, 12, 2)).upper()
    return value


def build_report(result):
    """Combine everything that was read into {section: {label: value}}."""
    ip = result["host"]
    errors = result["errors"]
    telnet, unknown = decode_telnet(result.get("telnet") or [])
    http = result.get("http") or {}
    pages = http.get("pages", {})
    device_info = pages.get("Deviceinfo.xml", {}).get("values", {})
    main_zone = pages.get("formMainZone_MainZoneXml.xml", {})
    heos = result.get("heos") or {}
    players = heos.get("players") or []
    player = next((p for p in players if p.get("ip") == ip), {})
    ssdp = result.get("discovery") or {}
    system = telnet.get("System", {})

    device = {}

    def put(label, *candidates):
        for candidate in candidates:
            if candidate not in (None, "", {}):
                device[label] = candidate if isinstance(candidate, dict) else str(candidate).strip()
                return

    put("Friendly name", system.pop("Friendly name", None),
        main_zone.get("values", {}).get("FriendlyName"), player.get("name"), ssdp.get("friendlyName"))
    put("Model", device_info.get("ManualModelName"), device_info.get("ModelName", "").lstrip("*"),
        player.get("model"), ssdp.get("modelName"), ssdp.get("looks_like"))
    put("Brand", BRANDS.get(device_info.get("BrandCode", "")), ssdp.get("manufacturer"))
    put("Category", device_info.get("CategoryName"))
    put("MAC address", _mac(device_info.get("MacAddress")))
    put("Serial number", player.get("serial"), ssdp.get("serialNumber"))
    put("Firmware", system.pop("Firmware", None))
    put("HEOS firmware", player.get("version"))
    put("Network", player.get("network"))
    put("Zones", device_info.get("DeviceZones"))
    if http:
        api = f"port {http['port']}"
        if device_info.get("CommApiVers"):
            api += f", API version {device_info['CommApiVers']}"
        put("Web API", api)

    report = {"Device": device}
    fallbacks = {
        "Status": _web_status(main_zone.get("values", {})),
        "Sources": _web_sources(main_zone.get("lists", {})),
    }
    for name in SECTION_ORDER:
        items = telnet.get(name) or fallbacks.get(name)
        if items:
            report[name] = items

    if heos:
        section = {}
        for label, key, field in (
            ("Volume", "get_volume", "level"),
            ("Mute", "get_mute", "state"),
            ("Play state", "get_play_state", "state"),
            ("Repeat", "get_play_mode", "repeat"),
            ("Shuffle", "get_play_mode", "shuffle"),
        ):
            value = heos.get(key, {}).get(field)
            if value:
                section[label] = value
        playing = heos.get("now_playing") or {}
        title = " - ".join(
            part for part in (playing.get("artist"), playing.get("song") or playing.get("station")) if part
        )
        if title:
            section["Now playing"] = title
        others = {
            p.get("name", "?"): f"{p.get('model', '?')} at {p.get('ip', '?')}"
            for p in players if p.get("ip") != ip
        }
        if others:
            section["Other HEOS players"] = others
        if section:
            report["HEOS"] = section

    if unknown:
        report["Other telnet replies"] = unknown[:60]

    notes = []
    answered = [key for key in ("telnet", "http", "heos") if result.get(key)]
    if not answered:
        notes.append(
            "Nothing answered at this address. Check that it is right, that this computer "
            "is on the same network, and that the receiver is on or its Network Control "
            "setting is Always On."
        )
    elif answered == ["heos"]:
        notes.append(
            "Only the HEOS interface answered. That is normal for HEOS speakers and music "
            "systems, which have no telnet control or web API."
        )
    elif "telnet" in errors:
        notes.append(
            f"Telnet control (port 23): {errors['telnet']}. The receiver allows one telnet "
            "client at a time, so close other control apps (Home Assistant, for example) "
            "and run this again for the full list of settings."
        )
    if report.get("Status", {}).get("Power") == "STANDBY":
        notes.append(
            "The receiver is in standby, and some settings are only reported while it is on. "
            "Switch it on and run this again for the full picture."
        )
    if notes:
        report["Notes"] = notes
    return report


def print_report(result):
    """Print one device's report as aligned text."""
    report = result["report"]
    device = report.get("Device", {})
    name = device.get("Model") or "Denon device"
    brand = device.get("Brand")
    if brand and brand.lower() not in name.lower():
        name = f"{brand} {name}"
    title = f"{name} at {result['host']}"
    print(f"\n{title}\n{'=' * len(title)}")
    for section, items in report.items():
        if not items:
            continue
        print(f"\n{section}")
        if isinstance(items, list):
            for line in items:
                print(textwrap.fill(line, width=78, initial_indent="  ", subsequent_indent="    "))
            continue
        for label, value in items.items():
            if isinstance(value, dict):
                print(f"  {label}")
                for key, val in value.items():
                    print(f"    {key:<26} {val}")
            else:
                print(f"  {label:<28} {value}")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Read the configuration of a Denon receiver on the local network. "
        "Only queries are sent, so no setting is changed.",
    )
    parser.add_argument("--host", help="the receiver's IP address (skips the network search)")
    parser.add_argument(
        "--subnet", default=DEFAULT_SUBNET,
        help=f"network to search when --host is not given (default {DEFAULT_SUBNET})",
    )
    parser.add_argument("--json", action="store_true", help="print everything as JSON instead of a report")
    parser.add_argument(
        "--save", nargs="?", const="", metavar="FILE",
        help="also save everything as JSON (default name: denon_<address>_<time>.json)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.2,
        help="seconds between telnet queries; raise it if settings are missing (default 0.2)",
    )
    args = parser.parse_args(argv)
    try:
        args.subnet = ipaddress.ip_network(args.subnet, strict=False)
    except ValueError as exc:
        parser.error(str(exc))
    if args.subnet.num_addresses > 1024:
        parser.error(f"{args.subnet} is too big to search; use a /24 such as {DEFAULT_SUBNET}")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")  # odd characters in names can't crash the report
    except AttributeError:
        pass

    if args.host:
        try:
            targets = {socket.gethostbyname(args.host): {"found_by": "--host"}}
        except OSError as exc:
            log(f"Cannot resolve {args.host}: {exc}")
            return 2
    else:
        targets = discover(args.subnet)
        if not targets:
            log(NOT_FOUND_HELP.format(subnet=args.subnet))
            return 1
        log("Found " + ", ".join(
            f"{ip} ({info.get('modelName') or info.get('looks_like') or 'Denon'})"
            for ip, info in targets.items()
        ))

    results = [read_device(ip, info, args.delay) for ip, info in targets.items()]
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            print_report(result)

    if args.save is not None:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        where = results[0]["host"] if len(results) == 1 else "all"
        path = args.save or f"denon_{where}_{stamp}.json"
        with open(path, "w", encoding="utf-8") as file:
            json.dump(results, file, indent=2, ensure_ascii=False)
        log(f"Saved {path}")
    return 0 if any(r["telnet"] or r["http"] or r["heos"] for r in results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
