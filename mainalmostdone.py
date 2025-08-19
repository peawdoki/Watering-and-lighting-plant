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


def read_multi_digit(max_value=9, x=0, y=0):
    num_str = ""
    lcd.move_to(x, y)
    while True:
        key = scan_keypad()
        if key:
            if key.isdigit():
                num_str += key
                lcd.putstr(key)
            elif key == '#':  # กดยืนยัน
                if num_str == "":
                    return -1
                val = int(num_str)
                if 0 <= val <= max_value:
                    return val
                else:
                    return -1
            elif key == '*':  # ยกเลิก
                return -1
        time.sleep(0.1)


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
    global data_control
    lcd.clear()
    lcd.putstr("Select Mode:")
    lcd.move_to(0, 1)
    lcd.putstr("1.Manual 2.Timer 3.Light Control")
    
    while True:
        key = scanKeypad()
        sleep(0.3)
        if key == "1":
            data_control[1] = "1"
            lcd.clear()
            lcd.putstr("Mode: Manual")
            sleep(1)
            break
        elif key == "2":
            data_control[1] = "2"
            lcd.clear()
            lcd.putstr("Mode: Timer")
            sleep(1)
            break
        elif key == "3":
            data_control[1] = "3"
            lcd.clear()
            lcd.putstr("Mode: Light Control")
            sleep(1)
            break
        if key == "#":
            break
        file_operation('w')

    return

def select_control_mode_pump():
    global data_control
    lcd.clear()
    lcd.putstr("Select Mode:")
    lcd.move_to(0, 1)
    lcd.putstr("1.Manual 2.Timer 3.Humid Control")
    
    while True:
        key = scanKeypad()
        sleep(0.3)
        if key == "1":
            data_control[7] = "1"
            lcd.clear()
            lcd.putstr("Mode: Manual")
            sleep(1)
            break
        elif key == "2":
            data_control[7] = "2"
            lcd.clear()
            lcd.putstr("Mode: Timer")
            sleep(1)
            break
        elif key == "3":
            data_control[7] = "3"
            lcd.clear()
            lcd.putstr("Mode: Humid Control")
            sleep(1)
            break
        if key == "#":
            break
        file_operation('w')

    return 

# === ฟังก์ชันควบคุมการทำงานม่านและปั๊ม ===
def devControl(light_value, humid2):
    datetime1 = ds.datetime()
    currTime = datetime1[4]*3600 + datetime1[5]*60 + datetime1[6]

    # Motor times
    start_time_motor = data_control[1]*3600 + data_control[2]*60 + data_control[3]
    stop_time_motor  = data_control[4]*3600 + data_control[5]*60 + data_control[6]

    # Pump times
    start_time_pump = data_control[8]*3600 + data_control[9]*60 + data_control[10]
    stop_time_pump  = data_control[11]*3600 + data_control[12]*60 + data_control[13]

    # ----------------- Motor Control -----------------
    if data_control[0] == 1:  # Manual
        if data_control[15] and not data_control[14]:
            motor_left()
            while not check_motor_sensors_for_open():
                sleep(0.1)
        elif not data_control[15] and data_control[14]:
            stop_motor()
            while not check_motor_sensors_for_close():
                sleep(0.1)

    elif data_control[0] == 2:  # Timer
        active = start_time_motor <= currTime <= stop_time_motor
        if active and not data_control[14]:
            motor_left()
            while not check_motor_sensors_for_open():
                sleep(0.1)
        elif not active and data_control[14]:
            motor_right()
            while not check_motor_sensors_for_close():
                sleep(0.1)

    elif data_control[0] == 3:  # Light
        active = start_time_motor <= currTime <= stop_time_motor
        if active:
            if light_value < data_control[18] and not data_control[14]:
                motor_left()
                while not check_motor_sensors_for_open():
                    sleep(0.1)
            elif light_value > data_control[19] and data_control[14]:
                motor_right()
                while not check_motor_sensors_for_close():
                    sleep(0.1)

    # ----------------- Pump Control -----------------
    if data_control[7] == 1:  # Manual
        if data_control[17] and not data_control[16]:
            pump_pwm.duty(data_control[22])
        elif not data_control[17] and data_control[16]:
            pump_pwm.duty(0)

    elif data_control[7] == 2:  # Timer
        active = start_time_pump <= currTime <= stop_time_pump
        if active and not data_control[16]:
            pump_pwm.duty(data_control[22])
        elif not active and data_control[16]:
            pump_pwm.duty(0)

    elif data_control[7] == 3:  # Humid
        active = start_time_pump <= currTime <= stop_time_pump
        if active:
            if humid2 < data_control[20] and not data_control[16]:
                pump_pwm.duty(data_control[22])
            elif humid2 > data_control[21] and data_control[16]:
                pump_pwm.duty(0)

        
def check_motor_sensors_for_close():
    s1 = sensor1.value()
    s2 = sensor2.value()
    if s1 == 1 and s2 == 1:
        stop_motor()
        return True
    return False

def check_motor_sensors_for_open():
    s1 = sensor1.value()
    s2 = sensor2.value()
    if s1 == 0 and s2 == 0:
        stop_motor()
        return True
    return False
            
def read_light_threshold():
    lcd.clear()
    lcd.putstr("1:Start 2:Stop")
    while True:
        key = scanKeypad()
        if key in ["1", "2"]:
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
                                data_control[18] = val
                            else:
                                data_control[19] = val
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
    lcd.clear()
    lcd.putstr("1:Start 2:Stop")
    while True:
        key = scanKeypad()
        if key in ["1", "2"]:
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
                                data_control[20] = val
                            else:
                                data_control[21] = val
                            lcd.clear()
                            lcd.putstr(f"Value set: {val}")
                            print(f"{'Start' if key=='1' else 'Stop'} Humid set to {val}%")
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
        data_control[23] = str(temp1)
    else:
        print("Read SN-300-BYH Fail")
    sleep(1)
    file_operation('w')
    

    req_ecth = [1, 3, 0, 0, 0, 3]
    raw2 = send_modbus_request(req_ecth)
    temp2, humi2, ec2 = parse_three_values(raw2)
    if temp2 is not None:
        print("Temp: {:.1f} °C, Humidity: {:.1f} %, EC: {:.1f} mS/cm".format(temp2, humi2, ec2))
        data_control[24] = str(humi2)
    else:
        print("Read SN-3000-ECTH Fail")
    sleep(1)
    file_operation('w')

    req_light = [7, 3, 0x01, 0xFA, 0x00, 0x02]
    raw3 = send_modbus_request(req_light)
    light_value = parse_light_data(raw3)
    if light_value is not None:
        print("Light Intensity:", light_value)
        data_control[25] = str(light_value)
    else:
        print("Read PR-300BYH-LUX Fail")
    sleep(3)
    file_operation('w')

    return temp1,humi1,light_value,humi2

def show_start_stop(idx_threshold, idx_time):
    lcd.clear()
    lcd.putstr("Start threshold: " + str(data_control[idx_threshold]))
    lcd.move_to(0, 1)
    lcd.putstr("Stop threshold: " + str(data_control[idx_threshold + 1]))

    sleep(2)

    lcd.clear()
    lcd.putstr("Start Time " + "{}:{}:{}".format(
        data_control[idx_time], data_control[idx_time + 1], data_control[idx_time + 2]))
    lcd.move_to(0, 1)
    lcd.putstr("Stop Time " + "{}:{}:{}".format(
        data_control[idx_time + 3], data_control[idx_time + 4], data_control[idx_time + 5]))



def check_dev_status():
    req_byh = [2, 3, 0, 0, 0, 2]
    raw1 = send_modbus_request(req_byh)
    temp1, humi1 = parse_two_values(raw1)
    sn300_status = "ON" if temp1 is not None else "OFF"

    req_ecth = [1, 3, 0, 0, 0, 3]
    raw2 = send_modbus_request(req_ecth)
    temp2, humi2, ec2 = parse_three_values(raw2)
    sn3000_status = "ON" if humid2 is not None else "OFF"

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
    lcd.clear()
    lcd.putstr("Select Menu (1-20): ")
    lcd.move_to(0,1)
    while True:
        key = read_multi_digit(max_value=20, x=3, y=1)  
        if not key:
            return

        if key == '1': #show date
            datetime1 = ds.datetime()   #(year, month, mday, weekday, hour, minute, second, 0)        
            lcd.putstr("Date:")            
            Date_str = str(datetime1[0]) + "/" + str(datetime1[1]) + "/" + str(datetime1[2]) + "/" + date1[datetime1[3]-1]
            lcd.move_to(0,1)
            lcd.putstr(Date_str)
        elif key == '2':
            #set date
            exitfunction()
        elif key == '3':
            #show time
            datetime1 = ds.datetime()   #(year, month, mday, weekday, hour, minute, second, 0)        
            lcd.putstr("Date:")            
            Time_str = str(datetime1[4]) + ":" + str(datetime1[5]) + ":" + str(datetime1[6])
            lcd.move_to(0,1)
            lcd.putstr(Time_str)
            exitfunction()
        elif key == '4':
            #set time
            exitfunction()
        elif key == '5':
            show_wifi_info()
            exitfunction()
        elif key == '6':
            connect_wifi()
            exitfunction()
        elif key == '7': #read Air Temp and humid
            lcd.clear()
            lcd.putstr("Air Temp and Humid")
            lcd.move_to(0, 1)
            lcd.putstr("Temp: " + str(temp1) + "C Humid: " + str(humi1) + "%")
            exitfunction()
        elif key == '8': #read Dirt humid
            lcd.clear()
            lcd.putstr("Dirt Humid")
            lcd.move_to(0, 1)
            lcd.putstr("Humidity: " + str(humi2) + "%")
            exitfunction()
        elif key == '10': #read light intensity
            lcd.clear()
            lcd.putstr("Light Intensity")
            lcd.move_to(0, 1)
            lcd.putstr("Intensity: " + str(light_value) + " lux")
            exitfunction()
        elif key == '11': 
            select_control_mode_motor()
            exitfunction()
        elif key == '12':
            select_control_mode_pump()
            exitfunction()
        elif key == '13':
            file_operation('r')
            data_control[15] = not data_control[15]
            file_operation('w')
            exitfunction()
        elif key == '14':
            file_operation('r')
            data_control[17] = not data_control[17]
            file_operation('w')
            exitfunction()
        elif key == '15':
            check_dev_status()
            exitfunction()
        elif key == '16':
            read_light_threshold()
            exitfunction()
        elif key == '17':#set time start light
            
            exitfunction()
        elif key == '18':
            read_humid_threshold()
            exitfunction()
        elif key == '19':#set time start humid

            exitfunction()
        elif key == '20':#show start time light
            show_start_stop(18, 1)
            exitfunction()
        elif key == '21':#show start time humid
            show_start_stop(20, 8)
            exitfunction()
        else:
            lcd.clear()
            lcd.putstr("Plese select 20")
            
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
    devConrol()
    
    
    
    
    
    




