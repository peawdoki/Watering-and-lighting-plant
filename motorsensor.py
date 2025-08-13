from time import sleep

# ===== ตัวแปรจำลอง =====
control_mode_motor = None
control_mode_pump = None
motorState = False
pumpState = False
motorStatus = "Off"
pumpStatus = "Off"
currTime = "12:00"
startTime1, stopTime1 = "08:00", "18:00"
startTime2, stopTime2 = "09:00", "17:00"
light_value = 200
light_threshold = 500
humid_value = 40
humid_threshold = 50
pump_power = 512

# ===== เซนเซอร์จำลอง =====
sensor1 = lambda: int(input("S1 (0/1): "))
sensor2 = lambda: int(input("S2 (0/1): "))

# ===== ฟังก์ชันจำลอง =====
def scanKeypad():
    return input("กดปุ่ม: ")

def motor_left():
    global motorStatus
    motorStatus = "On"
    print("Motor → ปิดม่าน")

def motor_right():
    global motorStatus
    motorStatus = "On"
    print("Motor → เปิดม่าน")

def stop_motor():
    global motorStatus
    motorStatus = "Off"
    print("Motor → หยุด")

class PumpPWM:
    def duty(self, val):
        global pumpStatus
        if val > 0:
            pumpStatus = "On"
            print(f"Pump → เปิด (power={val})")
        else:
            pumpStatus = "Off"
            print("Pump → ปิด")

pump_pwm = PumpPWM()

# ===== ฟังก์ชันเลือกโหมด =====
def select_control_mode_motor():
    global control_mode_motor
    print("Select Mode Motor:")
    print("1.Manual  2.Timer  3.Light Control")
    while True:
        key = scanKeypad()
        if key in ["1", "2", "3"]:
            control_mode_motor = key
            print(f"Motor Mode: {control_mode_motor}")
            break
        elif key == "#":
            break
    return control_mode_motor

def select_control_mode_pump():
    global control_mode_pump
    print("Select Mode Pump:")
    print("1.Manual  2.Timer  3.Humid Control")
    while True:
        key = scanKeypad()
        if key in ["1", "2", "3"]:
            control_mode_pump = key
            print(f"Pump Mode: {control_mode_pump}")
            break
        elif key == "#":
            break
    return control_mode_pump

# ===== ฟังก์ชันเช็คเซนเซอร์หยุดมอเตอร์ =====
def check_motor_sensors_for_close():
    s1 = sensor1()
    s2 = sensor2()
    if s1 == 1 and s2 == 1:
        stop_motor()
        return True
    return False

def check_motor_sensors_for_open():
    s1 = sensor1()
    s2 = sensor2()
    if s1 == 0 and s2 == 0:
        stop_motor()
        return True
    return False

# ===== ฟังก์ชันควบคุมอุปกรณ์ =====
def devControl():
    global currTime, motorState, pumpState, motorStatus, pumpStatus


    if control_mode_motor == "1":  # Manual
        if motorState and motorStatus != "On":
            motor_left()
            while not check_motor_sensors_for_close():
                sleep(0.1)
        elif not motorState and motorStatus != "On":
            motor_right()
            while not check_motor_sensors_for_open():
                sleep(0.1)

    elif control_mode_motor == "2":  # Timer
        active = startTime1 <= currTime <= stopTime1
        if active and motorStatus != "On":
            motor_left()
            while not check_motor_sensors_for_close():
                sleep(0.1)
        elif not active and motorStatus != "On":
            motor_right()
            while not check_motor_sensors_for_open():
                sleep(0.1)

    elif control_mode_motor == "3":  # Light
        active = startTime1 <= currTime <= stopTime1
        if active and light_value < light_threshold and motorStatus != "On":
            motor_left()
            while not check_motor_sensors_for_close():
                sleep(0.1)
        elif (not active or light_value >= light_threshold) and motorStatus != "On":
            motor_right()
            while not check_motor_sensors_for_open():
                sleep(0.1)

    # Pump Control
    if control_mode_pump == "1":  # Manual
        if pumpState and pumpStatus != "On":
            pump_pwm.duty(pump_power)
        elif not pumpState and pumpStatus != "Off":
            pump_pwm.duty(0)
    elif control_mode_pump == "2":  # Timer
        active = startTime2 <= currTime <= stopTime2
        if active and pumpStatus != "On":
            pump_pwm.duty(pump_power)
        elif not active and pumpStatus != "Off":
            pump_pwm.duty(0)
    elif control_mode_pump == "3":  # Humid
        active = startTime2 <= currTime <= stopTime2
        if active and humid_value < humid_threshold and pumpStatus != "On":
            pump_pwm.duty(pump_power)
        elif (not active or humid_value >= humid_threshold) and pumpStatus != "Off":
            pump_pwm.duty(0)

# ===== Main Loop =====
while True:
    key = scanKeypad()
    if key == "1":
        select_control_mode_motor()
    elif key == "2":
        select_control_mode_pump()
    elif key == "*":
        motorState = not motorState
        print("MotorState →", motorState)
    elif key == "0":
        pumpState = not pumpState
        print("PumpState →", pumpState)

    devControl()
