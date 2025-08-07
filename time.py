from machine import Pin, I2C
from ds3231 import DS3231
from i2c_lcd import I2cLcd
import time

# Keypad setup
keys = [['1','2','3','A'],
        ['4','5','6','B'],
        ['7','8','9','C'],
        ['*','0','#','D']]
rows = [Pin(i, Pin.OUT) for i in (33,25,14,13)]
cols = [Pin(i, Pin.IN, Pin.PULL_DOWN) for i in (15,2,4,23)]

# I2C and RTC setup
i2c = I2C(1, scl=Pin(22), sda=Pin(21), freq=400000)
rtc = DS3231(i2c)

def write_data_to_file(data):
    with open('time.txt','w') as f:
        for key, value in data.items():
            f.write(f"{key}:{value}\n")

def read_data_from_file(filename):
    data = {}
    with open(filename, 'r') as f:
        for line in f:
            key, value = line.strip().split(':')
            data[key] = value
    return data

readData = read_data_from_file('data.txt')
def show_time():
    current_time = rtc.datetime()
    h, m, s = current_time[4], current_time[5], current_time[6]
    now_str = f"{h:02}:{m:02}:{s:02}"
    lcd.move_to(0, 0)
    lcd.putstr(now_str + "         ")  # clear old chars
    return (h, m, s)

# LCD setup
lcd_addr = i2c.scan()[0]
lcd = I2cLcd(i2c, lcd_addr, 2, 16)

# Relay pin
relay = Pin(26, Pin.OUT)

# Time storage
start_time = None
end_time = None

def scan_keypad():
    for i, row in enumerate(rows):
        row.value(1)
        for j, col in enumerate(cols):
            if col.value() == 1:
                time.sleep(0.2)
                row.value(0)
                return keys[i][j]
        row.value(0)
    return None

def read_time_input(prompt):
    lcd.clear()
    lcd.putstr(prompt)
    print(prompt)
    time_input = ""
    while True:
        key = scan_keypad()
        if key:
            if key == "#":
                if len(time_input) == 6:
                    h = int(time_input[0:2])
                    m = int(time_input[2:4])
                    s = int(time_input[4:6])
                    lcd.clear()
                    lcd.putstr(f"{prompt}\n{h:02}:{m:02}:{s:02}")
                    print(f"{prompt} set to {h:02}:{m:02}:{s:02}")
                    time.sleep(1.5)
                    return (h, m, s)
                else:
                    lcd.clear()
                    lcd.putstr("NO Incomplete")
                    time_input = ""
            elif key == "*":
                time_input = ""
                lcd.clear()
                lcd.putstr("🔄 Input reset")
            elif key.isdigit() and len(time_input) < 6:
                time_input += key
                lcd.clear()
                lcd.putstr(prompt + "\n" + time_input)

def is_time_equal(current, target):
    return current[0] == target[0] and current[1] == target[1] and current[2] == target[2]

# Set ON/OFF time
start_time = read_time_input("Set ON Time:")
end_time = read_time_input("Set OFF Time:")

lcd.clear()
lcd.putstr("System Running...\nWaiting...")

# Main loop
while True:
    h, m, s = show_time()

    if is_time_equal((h, m, s), start_time):
        relay.value(1)
        lcd.move_to(0, 1)
        lcd.putstr("Device: ON  ")
        print("✅ Relay ON")

    elif is_time_equal((h, m, s), end_time):
        relay.value(0)
        lcd.move_to(0, 1)
        lcd.putstr("Device: OFF ")
        print("🛑 Relay OFF")

    time.sleep(0.5)
     
    data = {'start': start_time, 'stop':end_time }
    write_data_to_file(data)
