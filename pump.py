from machine import Pin, PWM
import time
from machine import SoftI2C
from lcd_api import LcdApi
from i2c_lcd import I2cLcd
from ds3231 import DS3231

# PWM Pin Setup
pwm_pin = Pin(12, Pin.OUT)
pwm = PWM(pwm_pin)
pwm.freq(1000)

# LCD Setup
I2C_ADDR = 0x27
totalRows = 2
totalColumns = 16
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=10000)
lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)

# Keypad Setup
keys = [['1','2','3','A'],
        ['4','5','6','B'],
        ['7','8','9','C'],
        ['*','0','#','D']]

# Define rows and columns for keypad
rows = [Pin(i, Pin.OUT) for i in (33,25,14,13)]  # Rows R1-R4
cols = [Pin(i, Pin.IN, Pin.PULL_DOWN) for i in (15,2,4,23)]  # Columns C1-C4

# Setup DS3231 RTC
rtc = DS3231(i2c)

def scan_keypad():
    for i, row in enumerate(rows):
        row.value(1)
        for j, col in enumerate(cols):
            if col.value() == 1:
                row.value(0)
                print(f"Key pressed: {keys[i][j]}")  # Debugging line to show the key pressed
                return keys[i][j]
        row.value(0)
    return None

# Function to read power input from keypad
def read_power():       
    num = ""    
    while True:
        key = scan_keypad()
        if key is not None :         
            if key >= '0' and key <= '9' and len(num) < 3:               
                num = num + key
                lcd.clear()
                lcd.putstr(f"Enter Power:{num}")
            elif key == '#':
                lcd.putstr("")                
                return int(num)
            elif key == '*':
                num = ""
                print("Enter Power: ", end="")

# Function to map input value to a specified range
def map_value(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

# Main loop
while True:
    key = scan_keypad()
    if key == '0'
         pwm.duty(0)
         lcd.putstr("Stop")
    if key == '1':  # If '1' is pressed, enter speed setting
        lcd.clear()
        lcd.putstr("Enter Speed: ")
        power_in = read_power()
        print(f"PowerIn: {power_in}")
        if 0 <= power_in <= 100:
            power_out = map_value(power_in, 0, 100, 0, 1023)
            print(f"PowerOut: {power_out}")
            pwm.duty(power_out)
            lcd.clear()
            lcd.putstr(f"Speed {power_in}%")
        else:
            lcd.clear()
            lcd.putstr("No Speed")