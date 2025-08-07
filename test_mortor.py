from machine import Pin, PWM, I2C
from time import sleep
import lcd_api
import i2c_lcd

# -------- Keypad Setup --------
keys = [['1','2','3','A'],
        ['4','5','6','B'],
        ['7','8','9','C'],
        ['*','0','#','D']]

rows = [Pin(i, Pin.OUT) for i in (4, 13, 14, 15)]
cols = [Pin(i, Pin.IN, Pin.PULL_DOWN) for i in (2, 23, 25, 33)]

def read_keypad():
    for i in range(4):
        rows[i].on()
        for j in range(4):
            if cols[j].value():
                rows[i].off()
                return keys[i][j]
        rows[i].off()
    return None

# -------- LCD Setup --------
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
lcd = i2c_lcd.I2cLcd(i2c, 0x27, 2, 16)  # อาจต้องปรับ address

# -------- Motor and Sensors --------
motor_r = PWM(Pin(26), freq=1000)
motor_l = PWM(Pin(27), freq=1000)

sensor1 = Pin(34, Pin.IN)
sensor2 = Pin(5, Pin.IN)

def stop_motor():
    motor_r.duty(0)
    motor_l.duty(0)

def motor_left(speed=512):
    motor_r.duty(speed)
    motor_l.duty(0)

def motor_right(speed=512):
    motor_r.duty(0)
    motor_l.duty(speed)

# -------- Main Loop --------
lcd.clear()
lcd.putstr("Ready")

while True:
    key = read_keypad()
    if key == '1':
        lcd.clear()
        lcd.putstr("LEFT...")
        motor_left()
        while True:
            s1 = sensor1.value()
            s2 = sensor2.value()
            lcd.move_to(0, 1)
            lcd.putstr(f"S1:{'ON ' if s1 else 'OFF'} S2:{'ON' if s2 else 'OFF'}")

            if s1 == 1 and s2 == 0:
                stop_motor()
                lcd.clear()
                lcd.putstr("ON")
                break
            sleep(0.1)

    elif key == '2':
        lcd.clear()
        lcd.putstr("RIGHT...")
        motor_right()
        while True:
            s1 = sensor1.value()
            s2 = sensor2.value()
            lcd.move_to(0, 1)
            lcd.putstr(f"S1:{'ON ' if s1 else 'OFF'} S2:{'ON' if s2 else 'OFF'}")

            if s2 == 1 and s1 == 0:
                stop_motor()
                lcd.clear()
                lcd.putstr("OFF")
                break
            sleep(0.1)

    sleep(0.1)
