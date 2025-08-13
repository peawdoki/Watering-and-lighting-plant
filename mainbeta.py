from machine import UART, Pin, PWM
from time import ticks_ms,sleep
from machine import SoftI2C
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

# === กำหนดขา DE/RE สำหรับ MAX485 ===
de = Pin(18, Pin.OUT)
re = Pin(5, Pin.OUT)

# LCD Setup
I2C_ADDR = 0x27
totalRows = 2
totalColumns = 16
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=10000)
lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)

# === กำหนด UART2 ===
uart2 = UART(2, baudrate=4800, tx=17, rx=16, bits=8, parity=None, stop=1)

# === เชื่อมต่อ WiFi ===
def connect_wifi(ssid, password, timeout=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(ssid, password)
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print('WiFi connection timeout')
                return False
            time.sleep(1)
    print('WiFi connected:', wlan.ifconfig()[0])
    return True

# === Firebase ===
SSID = 'LAPTOP-R0A00K9B 7400'
PASSWORD = 'U5r04*35'
FIREBASE_URL = 'https://test-dcf94-default-rtdb.asia-southeast1.firebasedatabase.app/'

data_control = ['0','0','0','0','0',False,False,'0','0','0','0',False,False,'0','0','0','0','LAPTOP-R0A00K9B 7400','U5r04*35','500']
            #    0   1   2   3   4   5      6    7   8   9   10  11    12    13  14  15  16   17                          18   19
# Keypad Setup
keys = [['1','2','3','A'],
        ['4','5','6','B'],
        ['7','8','9','C'],
        ['*','0','#','D']]

# Define rows and columns for keypad
rows = [Pin(i, Pin.OUT) for i in (33,25,14,13)]  # Rows R1-R4
cols = [Pin(i, Pin.IN, Pin.PULL_DOWN) for i in (15,2,4,23)]  # Columns C1-C4


def scan_keypad():
    for row in range(4):
        for r in rows:
            r.value(0)
        rows[row].value(1)
        for col in range(4):
            if cols[col].value() == 1:
                return keys[row][col]
    return None

def file_operation(mode):
    global data_control
    
    f = open('data1.txt', mode)
    if mode == 'r':
        data_str = f.readline()
        data_str = data_str[:len(data_str) - 1]    
        data_control = data_str.split(",")
    elif mode == 'w':
        data_str = ""     
        for x in data_control:
           data_str = data_str + str(x) + ','  # แปลง x เป็น string ก่อนเชื่อม
        data_str = data_str[:-1]
        data_str = data_str + '\n'     
        f.write(data_str)
    f.close()




def crc16(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc

def send_modbus_request(request):
    crc = crc16(request)
    request += [crc & 0xFF, (crc >> 8) & 0xFF]

    de.value(1)
    re.value(1)
    sleep(0.01)
    uart2.write(bytes(request))
    sleep(0.02)
    de.value(0)
    re.value(0)
    sleep(0.1)

    data = uart2.read(20)
    print("RECV:", data)
    return data

def parse_two_values(data):
    if data and len(data) >= 9:
        received_crc = (data[-1] << 8) + data[-2]
        calculated_crc = crc16(data[:-2])
        if received_crc != calculated_crc:
            print("CRC false")
            return None, None
        humi = (data[3] << 8) | data[4]
        temp = (data[5] << 8) | data[6]
        return round(temp * 0.1, 1), round(humi * 0.1, 1)
    return None, None

def parse_three_values(data):
    if data and len(data) >= 11:
        received_crc = (data[-1] << 8) + data[-2]
        calculated_crc = crc16(data[:-2])
        if received_crc != calculated_crc:
            print("CRC false")
            return None, None, None
        humi = (data[3] << 8) | data[4]
        temp = (data[5] << 8) | data[6]
        ec = (data[7] << 8) | data[8]
        return round(temp * 0.1, 1), round(humi * 0.1, 1), round(ec * 0.1, 1)
    return None, None, None

def parse_light_data(data):
    if data and len(data) >= 9:
        received_crc = (data[-1] << 8) + data[-2]
        calculated_crc = crc16(data[:-2])
        if received_crc != calculated_crc:
            print("CRC false")
            return None
        high = (data[3] << 8) + data[4]
        low = (data[5] << 8) + data[6]
        value = (high << 16) + low
        return value
    else:
        print("Not Full value")
        return None
    
# -------- Motor and Sensors detect --------
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
    
# === ฟังชันปั๊ม ===

pump_pwm_pin = Pin(12, Pin.OUT)
pump_pwm = PWM(pump_pwm_pin)
pump_pwm.freq(1000)

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

def map_value(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

def read_pump_Power():
    lcd.clear()
    lcd.putstr("Enter Pump Power: ")
    power_in = read_power()
    print(f"PowerIn: {power_in}")
    if 0 <= power_in <= 100:
        pump_power = map_value(power_in, 0, 100, 0, 1023)
        print(f"PowerOut: {pump_power}")
        lcd.clear()
        lcd.putstr(f"Pump Power: {power_in}%")
    else:
        lcd.clear()
        lcd.putstr("No Value")
    file_operation("w")
    pump_power = data_control[19]
    return pump_power

# === ฟังชันเลือกโหมดควบคุม ===
def select_control_mode_motor():
    global control_mode_motor
    lcd.clear()
    lcd.putstr("Select Mode:")
    lcd.move_to(0, 1)
    lcd.putstr("1.Manual 2.Timer 3.Light Control")
    
    while True:
        key = scanKeypad()
        sleep(0.3)
        if key == "1":
            control_mode_motor = "1"
            lcd.clear()
            lcd.putstr("Mode: Manual")
            sleep(1)
            break
        elif key == "2":
            control_mode_motor = "2"
            lcd.clear()
            lcd.putstr("Mode: Timer")
            sleep(1)
            break
        elif key == "3":
            control_mode_motor = "3"
            lcd.clear()
            lcd.putstr("Mode: Light Control")
            sleep(1)
            break
        if key == "#":
            break
    return control_mode_motor

def select_control_mode_pump():
    global control_mode_pump
    lcd.clear()
    lcd.putstr("Select Mode:")
    lcd.move_to(0, 1)
    lcd.putstr("1.Manual 2.Timer 3.Humid Control")
    
    while True:
        key = scanKeypad()
        sleep(0.3)
        if key == "1":
            control_mode_pump = "1"
            lcd.clear()
            lcd.putstr("Mode: Manual")
            sleep(1)
            break
        elif key == "2":
            control_mode_pump = "Timer"
            lcd.clear()
            lcd.putstr("Mode: Timer")
            sleep(1)
            break
        elif key == "3":
            control_mode_pump = "Humid"
            lcd.clear()
            lcd.putstr("Mode: Humid Control")
            sleep(1)
            break
        if key == "#":
            break
    return control_mode_pump

# === ฟังก์ชันควบคุมการทำงานม่านและปั๊ม ===
def devControl():
    global currTime, motorState, pumpState, control_mode_motor, control_mode_pump
    global start_time_motor, stop_time_motor, start_time_pump, stop_time_pump, start_time_pump2, stop_time_pump2, motorStatus, pumpStatus
    global light_value, start_light, humid_value, humid_threshold

    # ====== Motor Control ======
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
        active = start_time_motor <= currTime <= stop_time_motor
        if active and motorStatus != "On":
            motor_left()
            while not check_motor_sensors_for_close():
                sleep(0.1)
        elif not active and motorStatus != "On":
            motor_right()
            while not check_motor_sensors_for_open():
                sleep(0.1)

    elif control_mode_motor == "3":  
        active = start_time_motor <= currTime <= stop_time_motor

        if active:
            if light_value < start_light and motorStatus != "On":
                motor_left() 
                while not check_motor_sensors_for_open():  # รอจนม่านเปิดสุด
                    sleep(0.1)
            elif light_value > stop_light and motorStatus != "Off":
                motor_right()  
                while not check_motor_sensors_for_close():  # รอจนม่านปิดสนิท
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
        active = start_time_pump <= currTime <= stop_time_pump
        if active:
            if humid_d < start_humid and pumpStatus != "On":
                pump_pwm.duty(pump_power)
                   # sleep(0.1)
            elif light_value > stop_light and motorStatus != "Off":
                pump_pwm.duty(0)
                   # sleep(0.1)
            
def read_light_threshold():
    global start_light, stop_light
    lcd.clear()
    lcd.putstr("1:Start 2:Stop")
    while True:
        key = scanKeypad()
        if key == "1" or key == "2":
            lcd.clear()
            if key == "1":
                lcd.putstr("Set Start Light")
            else:
                lcd.putstr("Set Stop Light")
            val_str = ""
            while True:
                k = scanKeypad()
                if k == "#":  # ยืนยัน
                    try:
                        val = int(val_str)
                        if 0 <= val <= 200000:
                            if key == "1":
                                start_light = val
                            else:
                                stop_light = val
                            lcd.clear()
                            lcd.putstr(f"Value set: {val}")
                            print(f"{'Start' if key=='1' else 'Stop'} Light set to {val} lux")
                            return
                        else:
                            lcd.clear()
                            lcd.putstr("Out of range")
                            val_str = ""
                    except:
                        lcd.clear()
                        lcd.putstr("Invalid input")
                        val_str = ""
                elif k == "B":  # ยกเลิก
                    lcd.clear()
                    lcd.putstr("Cancelled")
                    return
                elif k.isdigit():
                    val_str += k
                    lcd.clear()
                    lcd.putstr(val_str)

def read_humid_threshold():
    global start_humid, stop_humid
    lcd.clear()
    lcd.putstr("1:Start 2:Stop")
    while True:
        key = scanKeypad()
        if key == "1" or key == "2":
            lcd.clear()
            if key == "1":
                lcd.putstr("Set Start Humid")
            else:
                lcd.putstr("Set Stop Humid")
            val_str = ""
            while True:
                k = scanKeypad()
                if k == "#":  # ยืนยัน
                    try:
                        val = int(val_str)
                        if 0 <= val <= 100:
                            if key == "1":
                                start_humid = val
                            else:
                                stop_humid = val
                            lcd.clear()
                            lcd.putstr(f"Value set: {val}")
                            print(f"{'Start' if key=='1' else 'Stop'} Humid set to {val} lux")
                            return
                        else:
                            lcd.clear()
                            lcd.putstr("Out of range")
                            val_str = ""
                    except:
                        lcd.clear()
                        lcd.putstr("Invalid input")
                        val_str = ""
                elif k == "B":  # ยกเลิก
                    lcd.clear()
                    lcd.putstr("Cancelled")
                    return
                elif k.isdigit():
                    val_str += k
                    lcd.clear()
                    lcd.putstr(val_str)

                    
    


# === ฟังก์ชันหลักที่รวมการอ่านทั้งหมด ===
def read_all_sensors():
    
    req_byh = [2, 3, 0, 0, 0, 2]
    raw1 = send_modbus_request(req_byh)
    temp1, humi1 = parse_two_values(raw1)
    if temp1 is not None:
        print("Temp: {:.1f} °C, Humidity: {:.1f} %".format(temp1, humi1))
        data_control[0] = str(temp1)
    else:
        print("Read SN-300-BYH Fail")
    sleep(1)
    file_operation('w')
    

    req_ecth = [1, 3, 0, 0, 0, 3]
    raw2 = send_modbus_request(req_ecth)
    temp2, humi2, ec2 = parse_three_values(raw2)
    if temp2 is not None:
        print("Temp: {:.1f} °C, Humidity: {:.1f} %, EC: {:.1f} mS/cm".format(temp2, humi2, ec2))
    else:
        print("Read SN-3000-ECTH Fail")
    sleep(1)

    req_light = [7, 3, 0x01, 0xFA, 0x00, 0x02]
    raw3 = send_modbus_request(req_light)
    light_value = parse_light_data(raw3)
    if light_value is not None:
        print("Light Intensity:", light_value)
    else:
        print("Read PR-300BYH-LUX Fail")
    sleep(3)
    
    return temp1,humi1,light_value,humi2



def check_device_status():
    req_byh = [2, 3, 0, 0, 0, 2]
    raw1 = send_modbus_request(req_byh)
    temp1, humi1 = parse_two_values(raw1)
    sn300_status = "ON" if temp1 is not None else "OFF"

    req_ecth = [1, 3, 0, 0, 0, 3]
    raw2 = send_modbus_request(req_ecth)
    temp2, humi2, ec2 = parse_three_values(raw2)
    sn3000_status = "ON" if temp2 is not None else "OFF"

    req_light = [7, 3, 0x01, 0xFA, 0x00, 0x02]
    raw3 = send_modbus_request(req_light)
    light_value = parse_light_data(raw3)
    lux_status = "ON" if light_value is not None else "OFF"
    
    motor_status = "ON" if (motor_l.duty() > 0 or motor_r.duty() > 0) else "OFF"
    pump_status = "ON" if pump_pwm_pin.value() else "OFF"

    print("\n=== Device Status ===")
    print("SN-300BYH: {} | SN-3000-ECTH: {} | PR-300BYH-LUX: {} | MOTOR: {} | PUMP: {}".format(
        sn300_status, sn3000_status, lux_status, motor_status, pump_status
    ))
    print("======================\n")
    
    lcd.clear()
    lcd.putstr("S1:{} S2:{} S3:{}\n".format(sn300_status, sn3000_status, lux_status))
    lcd.putstr("M:{}  P:{}".format(motor_status, pump_status))

    
def show_wifi_info():
    file_operation('r')
    lcd.clear()
    lcd.putstr("SSID: " + data_control[17])
    lcd.move_to(0, 1)
    lcd.putstr("Key: " + data_control[18])


    
    
    

def operation_esp32_comm():
    global pumpState,motorState
    lcd.clear()
    lcd.putstr("Select:1-14")
    while True:
        key = scan_keypad()
        if not key:
            return
        if key == '1':
            check_device_status()
            exitfunction()
        elif key == '2':
            lcd.clear()
            lcd.putstr("Air Temp and Humid")
            lcd.move_to(0, 1)
            lcd.putstr("Temp: " + str(temp1) + "C Humid: " + str(humi1) + "%")
            exitfunction()
        elif key == '3':
            lcd.clear()
            lcd.putstr("Dirt Humid")
            lcd.move_to(0, 1)
            lcd.putstr("Humidity: " + str(humi2) + "%")
            exitfunction()
        elif key == '4':
            lcd.clear()
            lcd.putstr("Light Intensity")
            lcd.move_to(0, 1)
            lcd.putstr("Intensity: " + str(light_value) + " lux")
            exitfunction()
        elif key == '5':
            show_wifi_info()
            exitfunction()
        elif key == '6':
            connect_wifi()
            exitfunction()
        elif key == '7':
            select_control_mode_motor()
            exitfunction()
        elif key == '8':
            select_control_mode_pump()
            motorState = not motorState
            exitfunction()
        elif key == '9':
            motorState = not motorState
            exitfunction()
        elif key == '10':
            pumpState = not pumpState
            exitfunction()
        elif key == '11':
            read_light_threshold()
            exitfunction()
        elif key == '12':
            read_humid_threshold()
            exitfunction()
        elif key == '13':
            
            exitfunction()
        elif key == '14':
            read_pump_Power()
            exitfunction()
        else:
            lcd.clear()
            lcd.putstr("1-14")
            
        sleep(1)
    
def exitfunction():
    t = ticks_ms()
    while not scan_keypad():
        if ticks_ms() - t > 5000:
            break
        sleep(0.1)
        
while True:
    temp1,humi1,light_value,humid2 = read_all_sensors()
    operation_esp32_comm()

    
    
    
    
    
    



