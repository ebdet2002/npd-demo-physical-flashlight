/*
 * Smart Adaptive Flashlight -- firmware v1
 * Target: ESP32-WROOM-32
 *
 * Sensors:
 *   - BH1750   ambient light sensor, I2C      (library: BH1750 by claws)
 *   - LIS3DH   accelerometer, I2C, hardware   (library: Adafruit_LIS3DH +
 *              click/double-click interrupt   Adafruit_Sensor)
 *
 * Actuator:
 *   - High-power LED driven via N-channel MOSFET (AO3400) gate, PWM from
 *     an ESP32 LEDC channel on LED_PWM_PIN.
 *
 * State machine (mirrors docs/SPEC.md "Interface Behavior / State Machine"):
 *   OFF --tap--> LOW --tap--> MED --tap--> HIGH --tap--> OFF
 *   any state except OFF --double-tap--> STROBE (toggle, remembers prior)
 *   OFF --double-tap--> SOS (toggle)
 *   long-press (>3s) on the tail-cap fallback switch --> OFF (hardware
 *   fallback, independent of accelerometer tap logic)
 *
 * Continuous behavior: while in LOW/MED/HIGH, ambient lux from the BH1750
 * scales the level's nominal duty cycle by 0.5x-1.2x every 2s, so the
 * user's selected *level* stays relative to ambient conditions.
 */

#include <Wire.h>
#include <BH1750.h>
#include <Adafruit_LIS3DH.h>
#include <Adafruit_Sensor.h>

// ---------------------------------------------------------------------------
// Pin map (matches pcb/generate_pcb.py U1_PINS reference designations)
// ---------------------------------------------------------------------------
static const int PIN_SDA        = 21;   // I2C data  -- shared BH1750 + LIS3DH
static const int PIN_SCL        = 22;   // I2C clock -- shared BH1750 + LIS3DH
static const int PIN_ACCEL_INT  = 32;   // LIS3DH INT1 (click/double-click)
static const int PIN_LED_PWM    = 25;   // MOSFET gate drive (LEDC PWM)
static const int PIN_FALLBACK_SW = 27;  // hardware long-press OFF fallback

static const int LEDC_CHANNEL   = 0;
static const int LEDC_FREQ_HZ   = 2000;    // above audible/flicker range
static const int LEDC_RES_BITS  = 10;      // 0-1023 duty range
static const int LEDC_MAX_DUTY  = (1 << LEDC_RES_BITS) - 1;

// ---------------------------------------------------------------------------
// Brightness levels: nominal duty cycle (0-1023) before ambient scaling.
// Values derived from docs/SPEC.md power budget (LOW ~150lm/80mA ...
// HIGH ~1000lm/900mA at the LED's rated forward current).
// ---------------------------------------------------------------------------
enum Level { OFF = 0, LOW_LEVEL, MED_LEVEL, HIGH_LEVEL, NUM_LEVELS };
static const int NOMINAL_DUTY[NUM_LEVELS] = {0, 90, 350, 1023};

enum Mode { MODE_NORMAL, MODE_STROBE, MODE_SOS };

BH1750 lightMeter;
Adafruit_LIS3DH accel = Adafruit_LIS3DH();

Level currentLevel = OFF;
Level levelBeforeStrobe = LOW_LEVEL;
Mode currentMode = MODE_NORMAL;

float ambientLux = 100.0;
unsigned long lastAmbientReadMs = 0;
static const unsigned long AMBIENT_READ_INTERVAL_MS = 2000;

unsigned long fallbackPressStartMs = 0;
bool fallbackPressed = false;

// SOS timing (Morse: ... --- ...), in milliseconds.
static const int SOS_DOT_MS = 200;
static const int SOS_DASH_MS = 600;
static const int SOS_GAP_MS = 200;
static const int SOS_LETTER_GAP_MS = 600;
static const int SOS_WORD_GAP_MS = 1400;

static const int STROBE_ON_MS = 50;
static const int STROBE_OFF_MS = 50;

volatile bool singleTapFlag = false;
volatile bool doubleTapFlag = false;

void IRAM_ATTR onAccelInterrupt() {
  // LIS3DH's hardware click engine flags single vs. double click in its
  // CLICK_SRC register; we just note "an interrupt happened" here and let
  // loop() read the register (fast, non-blocking ISR body).
  singleTapFlag = true;  // resolved to single/double in loop() via register read
}

void setup() {
  Serial.begin(115200);
  Wire.begin(PIN_SDA, PIN_SCL);

  pinMode(PIN_ACCEL_INT, INPUT);
  pinMode(PIN_FALLBACK_SW, INPUT_PULLUP);

  // --- Ambient light sensor ---
  if (!lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("BH1750 not found -- check wiring, defaulting ambient=100lux");
  }

  // --- Accelerometer: configure hardware click detection ---
  if (!accel.begin(0x19)) {
    Serial.println("LIS3DH not found -- tap interaction disabled this boot");
  } else {
    accel.setRange(LIS3DH_RANGE_2_G);
    accel.setClick(2, 60);  // click type: both single+double, 60 = threshold
    attachInterrupt(digitalPinToInterrupt(PIN_ACCEL_INT), onAccelInterrupt, RISING);
  }

  // --- PWM / LEDC setup for the LED driver MOSFET gate ---
  ledcSetup(LEDC_CHANNEL, LEDC_FREQ_HZ, LEDC_RES_BITS);
  ledcAttachPin(PIN_LED_PWM, LEDC_CHANNEL);
  ledcWrite(LEDC_CHANNEL, 0);

  Serial.println("Smart Adaptive Flashlight v1 booted.");
}

// ---------------------------------------------------------------------------
// Tap handling: read the LIS3DH CLICK_SRC register to disambiguate single
// vs. double click, then drive the state machine.
// ---------------------------------------------------------------------------
void handleAccelInterrupt() {
  uint8_t click = accel.getClick();
  if (click == 0) return;

  bool isDouble = (click & 0x20) != 0;  // DCLICK bit
  bool isSingle = (click & 0x10) != 0;  // SCLICK bit

  if (isDouble) {
    onDoubleTap();
  } else if (isSingle) {
    onSingleTap();
  }
}

void onSingleTap() {
  if (currentMode != MODE_NORMAL) {
    // A single tap while strobing/SOS has no effect in v1 -- only
    // double-tap toggles out of those modes, per the SPEC state machine.
    return;
  }
  currentLevel = static_cast<Level>((currentLevel + 1) % NUM_LEVELS);
  Serial.printf("Single tap -> level %d\n", currentLevel);
}

void onDoubleTap() {
  if (currentLevel == OFF && currentMode == MODE_NORMAL) {
    currentMode = MODE_SOS;
    Serial.println("Double tap from OFF -> SOS");
    return;
  }
  if (currentMode == MODE_NORMAL) {
    levelBeforeStrobe = currentLevel;
    currentMode = MODE_STROBE;
    Serial.println("Double tap -> STROBE");
  } else {
    // Toggle back to whatever normal level was active before.
    currentMode = MODE_NORMAL;
    currentLevel = levelBeforeStrobe;
    Serial.println("Double tap -> back to NORMAL");
  }
}

// ---------------------------------------------------------------------------
// Hardware long-press fallback: tail-cap momentary switch, independent of
// the accelerometer, in case of sensor fault.
// ---------------------------------------------------------------------------
void handleFallbackSwitch() {
  bool pressed = (digitalRead(PIN_FALLBACK_SW) == LOW);
  unsigned long now = millis();

  if (pressed && !fallbackPressed) {
    fallbackPressed = true;
    fallbackPressStartMs = now;
  } else if (pressed && fallbackPressed) {
    if (now - fallbackPressStartMs > 3000) {
      currentLevel = OFF;
      currentMode = MODE_NORMAL;
      Serial.println("Long-press fallback -> OFF");
    }
  } else if (!pressed) {
    fallbackPressed = false;
  }
}

// ---------------------------------------------------------------------------
// Ambient-light-adaptive baseline: scale the nominal duty cycle for the
// current level by a 0.5x-1.2x multiplier derived from measured lux.
// Bright environment -> dim down (save battery, avoid overexposure).
// Dark environment    -> brighten up (actual visibility need).
// ---------------------------------------------------------------------------
float ambientMultiplier(float lux) {
  // Piecewise-linear map, clamped to [0.5, 1.2].
  //   lux <= 10    (near darkness)        -> 1.2x
  //   lux >= 500   (bright warehouse/day) -> 0.5x
  //   linear in between
  if (lux <= 10.0) return 1.2;
  if (lux >= 500.0) return 0.5;
  float t = (lux - 10.0) / (500.0 - 10.0);
  return 1.2 - t * (1.2 - 0.5);
}

void updateAmbientReading() {
  unsigned long now = millis();
  if (now - lastAmbientReadMs < AMBIENT_READ_INTERVAL_MS) return;
  lastAmbientReadMs = now;

  float lux = lightMeter.readLightLevel();
  if (lux >= 0) {
    ambientLux = lux;
  }
}

// ---------------------------------------------------------------------------
// Output drivers for each mode.
// ---------------------------------------------------------------------------
void driveNormal() {
  int nominal = NOMINAL_DUTY[currentLevel];
  float mult = ambientMultiplier(ambientLux);
  int duty = constrain((int)(nominal * mult), 0, LEDC_MAX_DUTY);
  ledcWrite(LEDC_CHANNEL, duty);
}

void driveStrobe() {
  unsigned long phase = millis() % (STROBE_ON_MS + STROBE_OFF_MS);
  ledcWrite(LEDC_CHANNEL, phase < STROBE_ON_MS ? LEDC_MAX_DUTY : 0);
}

// Simple blocking-free SOS pattern player, driven off millis().
void driveSOS() {
  // Pattern encoded as a sequence of (on_ms, off_ms) pulses: S=... O=---
  static const int PATTERN_ON[]  = {
    SOS_DOT_MS, SOS_DOT_MS, SOS_DOT_MS,
    SOS_DASH_MS, SOS_DASH_MS, SOS_DASH_MS,
    SOS_DOT_MS, SOS_DOT_MS, SOS_DOT_MS
  };
  static const int PATTERN_OFF[] = {
    SOS_GAP_MS, SOS_GAP_MS, SOS_LETTER_GAP_MS,
    SOS_GAP_MS, SOS_GAP_MS, SOS_LETTER_GAP_MS,
    SOS_GAP_MS, SOS_GAP_MS, SOS_WORD_GAP_MS
  };
  static const int PATTERN_LEN = sizeof(PATTERN_ON) / sizeof(PATTERN_ON[0]);

  static int step = 0;
  static unsigned long stepStartMs = 0;
  static bool inOnPhase = true;

  unsigned long now = millis();
  if (stepStartMs == 0) stepStartMs = now;

  unsigned long elapsed = now - stepStartMs;
  unsigned long onDur = PATTERN_ON[step];
  unsigned long offDur = PATTERN_OFF[step];

  if (inOnPhase) {
    ledcWrite(LEDC_CHANNEL, LEDC_MAX_DUTY);
    if (elapsed >= onDur) {
      inOnPhase = false;
      stepStartMs = now;
    }
  } else {
    ledcWrite(LEDC_CHANNEL, 0);
    if (elapsed >= offDur) {
      inOnPhase = true;
      stepStartMs = now;
      step = (step + 1) % PATTERN_LEN;
    }
  }
}

void loop() {
  if (singleTapFlag) {
    singleTapFlag = false;
    handleAccelInterrupt();
  }

  handleFallbackSwitch();
  updateAmbientReading();

  switch (currentMode) {
    case MODE_NORMAL:
      driveNormal();
      break;
    case MODE_STROBE:
      driveStrobe();
      break;
    case MODE_SOS:
      driveSOS();
      break;
  }
}
