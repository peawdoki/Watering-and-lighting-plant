from machine import UART, Pin
import uasyncio as asyncio
from time import sleep

# === กำหนดขา DE/RE สำหรับ MAX485 ===
de = Pin(18, Pin.OUT)
re = Pin(5, Pin.OUT)

# === กำหนด UART2 ===
uart2 = UART(2, baudrate=4800, tx=17, rx=16, bits=8, parity=None, stop=1)

def scan_keypad():
    for row in range(4):
        for r in rows:
            r.value(0)
        rows[row].value(1)
        for col in range(4):
            if cols[col].value() == 1:
                return keys[row][col]
    return None

def write_data_to_file(data):
    with open('data.txt', 'w') as f:
        for key, value in data.items():
            f.write(f"{key}:{value}\n")

def read_data_from_file(filename):
    data = {}
    with open(filename, 'r') as f:
        for line in f:
            key, value = line.strip().split(':')
            data[key] = value
    return data

def read_num()

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
    
# === ฟังก์ชันควบคุมการทำงานม่านและปั๊ม ===
def devControl():
    global startTime1, stopTime1, startTime2, stopTime2, motorStatus, pumpStatus, timerState, currTime
    active1 = startTime1 <= currTime <= stopTime1
    active2 = startTime2 <= currTime <= stopTime2

    if timerMotorState:
            if active1 and motorState:
                if motorStatus != "On":
                    lcd.clear()
                    lcd.putstr("Motor On")
                    motorStatus = "On"
                    lcdCleared = True
            else:
                if motorStatus != "Off":
                    lcd.clear()
                    lcd.putstr("Motor Off")
                    motorStatus = "Off"
                    lcdCleared = True

    if timerPumpState:
            if active2 and pumpState:
                if pumpStatus != "On":
                    lcd.clear()
                    lcd.putstr("Pump On")
                    pumpStatus = "On"
                    lcdCleared = True
            else:
                if pumpStatus != "Off":
                    lcd.clear()
                    lcd.putstr("Pump Off")
                    pumpStatus = "Off"
                    lcdCleared = True
    


# === ฟังก์ชันหลักที่รวมการอ่านทั้งหมด ===
def read_all_sensors_and_save():
    
    req_byh = [2, 3, 0, 0, 0, 2]
    raw1 = send_modbus_request(req_byh)
    temp1, humi1 = parse_two_values(raw1)
    if temp1 is not None:
        print("Temp: {:.1f} °C, Humidity: {:.1f} %".format(temp1, humi1))
    else:
        print("Read SN-300-BYH Fail")
    sleep(1)

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
    
    return temp1,humi1,light_value,humid2



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

    motor_status = "ON" if motor_pin.value() else "OFF"
    pump_status = "ON" if pump_pin.value() else "OFF"

    print("\n=== Device Status ===")
    print("SN-300BYH: {} | SN-3000-ECTH: {} | PR-300BYH-LUX: {} | MOTOR: {} | PUMP: {}".format(
        sn300_status, sn3000_status, lux_status, motor_status, pump_status
    ))
    print("======================\n")
    
    lcd.clear()
    lcd.putstr("S1:{} S2:{} S3:{}\n".format(sn300_status, sn3000_status, lux_status))
    lcd.putstr("M:{}  P:{}".format(motor_status, pump_status))

    
def show_wifi_info():
    try:
        with open("datapae.txt", "r") as f:
            line = f.readline().strip()
            ssid, password = line.split(",")  # แยก SSID และ Password

        # แสดงบน LCD (2 บรรทัด)
        lcd.clear()
        lcd.putstr("SSID: " + ssid)
        lcd.move_to(0, 1)
        lcd.putstr("Key: " + password)

    except Exception as e:
        print("Error reading datapae.txt:", e)
        if lcd_ready:
            lcd.clear()
            lcd.putstr("Read Error")
    
def keypad_com():
    lcd.clear()
    lcd.putstr("Select:1-14")
    while True:
        key = scan_keypad()
        if key == '1':
            check_device_status
            exitfunction()
        elif key == '2':
            lcd.putstr("Air Temp and Humid")
            lcd.putstr("Temp: {temp1}C, Humidity: {humi1}%")
            exitfunction()
        elif key == '3':
            lcd.putstr("Dirt Humid")
            lcd.putstr("Humidity: {humi2}%")
            exitfunction()
        elif key == '4':
            lcd.putstr("Light Intensity")
            lcd.putstr("Intensity: {light_value} lux")
            exitfunction()
        elif key == '5':
            show_wifi_info()
            exitfunction()
        elif key == '6':
            
            exitfunction()
        elif key == '7':
            
            exitfunction()
        elif key == '8':
            
            exitfunction()
        elif key == '9':
            exitfunction()
        elif key == '10':
            exitfunction()
        elif key == '11':
            exitfunction()
        elif key == '12':
            exitfunction()
        elif key == '13':
            
            exitfunction()
        elif key == '14':
            
            exitfunction()
        else:
            lcd.clear
            lcd.putstr("please enter 1-14")
            
        sleep(0.1)
    
def exitfunction():
    lcd.move_to(0, 1)
    lcd.putstr("Press B to back")
    while True:
        key = scan_keypad()
        if key == 'B':
            select_function()
            break
        sleep(0.1)
        
        
while True:
    
    temp1,humi1,light_value,humid2 = read_all_sensors_and_save()
    
    keypad_com()
    
    
    
    if light_value >= float(startlight) and light_value <= float(stoplight):
        motorState = True
    else:
        motorState = False

    
    if humid2 >= float(startHumid) and humid2 <= float(stopHumid):
        pumpState = True
    else:
        pumpState = False
