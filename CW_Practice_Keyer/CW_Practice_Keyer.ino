/*
 * CW_Practice_Keyer
 *
 * GCARC / W2MMD Arduino sketch: Morse (CW) practice keyer and beacon.
 *
 * Hardware (Arduino Uno or compatible):
 *   - Straight key or pushbutton between KEY_PIN and GND
 *     (internal pull-up; key-down is LOW)
 *   - Piezo speaker or small audio amp between TONE_PIN and GND
 *   - Onboard LED on LED_PIN shows key-down / transmitting
 *
 * Serial Monitor at 9600 baud. Type help for commands.
 *
 * Default beacon text is a club CQ. Change CALLSIGN or use the
 * serial "msg" command before putting this on the air.
 */

const int KEY_PIN = 2;
const int TONE_PIN = 8;
const int LED_PIN = LED_BUILTIN;

const int SIDETONE_HZ = 600;
const int DEFAULT_WPM = 18;
const char DEFAULT_MESSAGE[] = "CQ CQ DE W2MMD W2MMD K";

enum OperatingMode {
  MODE_KEY,
  MODE_AUTO
};

int wpm = DEFAULT_WPM;
OperatingMode mode = MODE_KEY;
char message[96];
bool autoSending = false;
unsigned long nextAutoSendMs = 0;
const unsigned long AUTO_REPEAT_MS = 10000;

int unitMs() {
  // Standard PARIS timing: 50 units per word.
  return 1200 / wpm;
}

void keyDown() {
  digitalWrite(LED_PIN, HIGH);
  tone(TONE_PIN, SIDETONE_HZ);
}

void keyUp() {
  noTone(TONE_PIN);
  digitalWrite(LED_PIN, LOW);
}

void sendDit() {
  keyDown();
  delay(unitMs());
  keyUp();
  delay(unitMs());
}

void sendDah() {
  keyDown();
  delay(unitMs() * 3);
  keyUp();
  delay(unitMs());
}

// Returns ITU Morse as '.' and '-' for A-Z, 0-9, and a few punctuation marks.
const char *morseFor(char c) {
  if (c >= 'a' && c <= 'z') {
    c = c - 'a' + 'A';
  }

  switch (c) {
    case 'A': return ".-";
    case 'B': return "-...";
    case 'C': return "-.-.";
    case 'D': return "-..";
    case 'E': return ".";
    case 'F': return "..-.";
    case 'G': return "--.";
    case 'H': return "....";
    case 'I': return "..";
    case 'J': return ".---";
    case 'K': return "-.-";
    case 'L': return ".-..";
    case 'M': return "--";
    case 'N': return "-.";
    case 'O': return "---";
    case 'P': return ".--.";
    case 'Q': return "--.-";
    case 'R': return ".-.";
    case 'S': return "...";
    case 'T': return "-";
    case 'U': return "..-";
    case 'V': return "...-";
    case 'W': return ".--";
    case 'X': return "-..-";
    case 'Y': return "-.--";
    case 'Z': return "--..";
    case '0': return "-----";
    case '1': return ".----";
    case '2': return "..---";
    case '3': return "...--";
    case '4': return "....-";
    case '5': return ".....";
    case '6': return "-....";
    case '7': return "--...";
    case '8': return "---..";
    case '9': return "----.";
    case '.': return ".-.-.-";
    case ',': return "--..--";
    case '?': return "..--..";
    case '/': return "-..-.";
    case '=': return "-...-";
    default:  return 0;
  }
}

void sendCharacter(char c) {
  if (c == ' ') {
    delay(unitMs() * 7);
    return;
  }

  const char *code = morseFor(c);
  if (!code) {
    return;
  }

  for (int i = 0; code[i] != '\0'; i++) {
    if (code[i] == '.') {
      sendDit();
    } else if (code[i] == '-') {
      sendDah();
    }
  }
  delay(unitMs() * 2);  // already waited 1 unit after the last element
}

void sendMessage(const char *text) {
  Serial.print(F("Sending: "));
  Serial.println(text);

  for (int i = 0; text[i] != '\0'; i++) {
    sendCharacter(text[i]);
  }
  keyUp();
}

void printHelp() {
  Serial.println(F("CW Practice Keyer"));
  Serial.println(F("  help          this list"));
  Serial.println(F("  status        show WPM, mode, and message"));
  Serial.println(F("  wpm <n>       set speed (5-40)"));
  Serial.println(F("  msg <text>    set auto/beacon text"));
  Serial.println(F("  send          send the message once"));
  Serial.println(F("  mode key      straight-key practice"));
  Serial.println(F("  mode auto     repeat the message"));
  Serial.println(F("  stop          stop auto sending"));
}

void printStatus() {
  Serial.print(F("WPM="));
  Serial.print(wpm);
  Serial.print(F("  mode="));
  Serial.print(mode == MODE_KEY ? F("key") : F("auto"));
  Serial.print(F("  msg="));
  Serial.println(message);
}

void handleCommand(char *line) {
  // Trim trailing CR/LF/spaces.
  int len = strlen(line);
  while (len > 0 && (line[len - 1] == '\r' || line[len - 1] == '\n' || line[len - 1] == ' ')) {
    line[--len] = '\0';
  }
  if (len == 0) {
    return;
  }

  if (strcmp(line, "help") == 0) {
    printHelp();
  } else if (strcmp(line, "status") == 0) {
    printStatus();
  } else if (strncmp(line, "wpm ", 4) == 0) {
    int value = atoi(line + 4);
    if (value < 5 || value > 40) {
      Serial.println(F("WPM must be 5 to 40"));
    } else {
      wpm = value;
      printStatus();
    }
  } else if (strncmp(line, "msg ", 4) == 0) {
    strncpy(message, line + 4, sizeof(message) - 1);
    message[sizeof(message) - 1] = '\0';
    printStatus();
  } else if (strcmp(line, "send") == 0) {
    sendMessage(message);
  } else if (strcmp(line, "mode key") == 0) {
    mode = MODE_KEY;
    autoSending = false;
    keyUp();
    printStatus();
  } else if (strcmp(line, "mode auto") == 0) {
    mode = MODE_AUTO;
    autoSending = true;
    nextAutoSendMs = millis();
    printStatus();
  } else if (strcmp(line, "stop") == 0) {
    autoSending = false;
    keyUp();
    Serial.println(F("Auto send stopped"));
  } else {
    Serial.println(F("Unknown command. Type help"));
  }
}

void readSerialCommands() {
  static char line[96];
  static int index = 0;

  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      line[index] = '\0';
      handleCommand(line);
      index = 0;
    } else if (index < (int)sizeof(line) - 1) {
      line[index++] = c;
    }
  }
}

void setup() {
  pinMode(KEY_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  pinMode(TONE_PIN, OUTPUT);
  keyUp();

  strncpy(message, DEFAULT_MESSAGE, sizeof(message) - 1);
  message[sizeof(message) - 1] = '\0';

  Serial.begin(9600);
  delay(200);
  Serial.println();
  printHelp();
  printStatus();
  Serial.println(F("Close the key to GND on pin 2 to practice."));
}

void loop() {
  readSerialCommands();

  if (mode == MODE_KEY) {
    static bool wasKeyed = false;
    bool keyed = digitalRead(KEY_PIN) == LOW;
    if (keyed && !wasKeyed) {
      keyDown();
    } else if (!keyed && wasKeyed) {
      keyUp();
    }
    wasKeyed = keyed;
  } else if (autoSending && (long)(millis() - nextAutoSendMs) >= 0) {
    sendMessage(message);
    nextAutoSendMs = millis() + AUTO_REPEAT_MS;
  }
}
