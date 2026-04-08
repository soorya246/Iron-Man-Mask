import RPi.GPIO as GPIO
import time
import subprocess
from rpi_ws281x import PixelStrip, Color

# ── LED Setup ────────────────────────────────────────
LED_PIN        = 18       # Must be GPIO 18 (hardware PWM)
LED_COUNT      = 64
LED_BRIGHTNESS = 40
LED_FREQ_HZ    = 800000
LED_DMA        = 10
LED_INVERT     = False
LED_CHANNEL    = 0

# ── Pin Definitions (BCM numbering) ──────────────────
TRIG_PIN    = 23
ECHO_PIN    = 24
BUZZER_PIN  = 25

# ── Alert Zones (cm) ─────────────────────────────────
DANGER_ZONE  = 20
WARNING_ZONE = 60

# ── State Tracking ────────────────────────────────────
last_zone = -1

# ── GPIO Setup ───────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(TRIG_PIN,   GPIO.OUT)
GPIO.setup(ECHO_PIN,   GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

buzzer_pwm = GPIO.PWM(BUZZER_PIN, 1000)  # 1kHz tone

# ── LED Strip Setup ───────────────────────────────────
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ,
                   LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# ─────────────────────────────────────────────────────
def set_all_leds(r, g, b):
    """Fill entire LED matrix with one color."""
    color = Color(r, g, b)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

# ─────────────────────────────────────────────────────
def get_distance():
    """Trigger HC-SR04 and return distance in cm."""
    GPIO.output(TRIG_PIN, False)
    time.sleep(0.000002)
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    timeout_start = time.time()

    # Wait for echo to go HIGH
    while GPIO.input(ECHO_PIN) == 0:
        if time.time() - timeout_start > 0.03:
            return -1   # sensor timeout
    pulse_start = time.time()

    # Wait for echo to go LOW
    while GPIO.input(ECHO_PIN) == 1:
        if time.time() - pulse_start > 0.03:
            return -1   # object too far
    pulse_end = time.time()

    elapsed  = pulse_end - pulse_start
    distance = (elapsed * 34300) / 2   # speed of sound → cm
    return round(distance, 1)

# ─────────────────────────────────────────────────────
def speak(text):
    """Speak a phrase using espeak — runs without blocking."""
    subprocess.Popen(
        ['espeak', '-s', '130', '-a', '200', '-v', 'en', text],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# ─────────────────────────────────────────────────────
def alert_buzz(on_ms, off_ms):
    """Buzz for on_ms milliseconds, pause for off_ms."""
    buzzer_pwm.start(50)              # 50% duty cycle
    time.sleep(on_ms  / 1000.0)
    buzzer_pwm.stop()
    time.sleep(off_ms / 1000.0)

# ─────────────────────────────────────────────────────
def cleanup():
    """Turn off everything and release GPIO."""
    set_all_leds(0, 0, 0)
    buzzer_pwm.stop()
    GPIO.cleanup()
    print("\nCleaned up. Goodbye!")

# ── Main Loop ─────────────────────────────────────────
print("Obstacle detector running. Press Ctrl+C to stop.")

try:
    while True:
        distance = get_distance()

        if distance == -1:
            print("Sensor error / out of range")
            time.sleep(0.2)
            continue

        print(f"Distance: {distance} cm")

        if distance <= DANGER_ZONE:
            # ── DANGER: Too close ──
            alert_buzz(80, 80)
            set_all_leds(255, 0, 0)      # Red
            if last_zone != 1:
                speak("Too close")        # ← Says exactly "Too close"
                last_zone = 1

        elif distance <= WARNING_ZONE:
            # ── WARNING: Getting close ──
            alert_buzz(200, 400)
            set_all_leds(255, 165, 0)    # Orange
            if last_zone != 2:
                speak("Warning")          # ← Says exactly "Warning"
                last_zone = 2

        else:
            # ── SAFE ──
            buzzer_pwm.stop()
            set_all_leds(0, 255, 0)      # Green
            last_zone = 0
            time.sleep(0.1)

except KeyboardInterrupt:
    cleanup()