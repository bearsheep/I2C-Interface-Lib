import time

import ft4222.GPIO as GPIO

from .i2c_base import I2CDeviceBase
from .ft4222_device import FT4222I2CDevice


class I2C_FT4222(I2CDeviceBase):
    """
        self.slave_addr : Input slave address(8-bit Address).\n
        self.print_debug : Print log = 1; Not to print log = 0; \n
        """
    # GPIO 方向常數，讓外部呼叫者不需要直接 import ft4222.GPIO
    DIR_INPUT  = GPIO.Dir.INPUT
    DIR_OUTPUT = GPIO.Dir.OUTPUT

    def __init__(self, description="FT4222 A", print_debug=0, slave_addr=0xA0, speed=400):
        self.slave_addr = slave_addr >> 1   # 8-bit -> 7-bit, same convention as I2C_ISS
        self.print_debug = print_debug
        self.device = FT4222I2CDevice(description=description)
        self.device.connect(speed_khz=speed)

    def I2C_READ(self, address, number):
        self.device.i2c_write_ex(self.slave_addr, FT4222I2CDevice.FLAG_START, bytes([address]))
        rx_buff = list(self.device.i2c_read_ex(self.slave_addr, FT4222I2CDevice.FLAG_START_AND_STOP, number))
        if self.print_debug:
            print("Read byte 0x%02X value = " % address + str.join("", ("0x%02X, " % a for a in rx_buff)))
        return rx_buff

    def I2C_WRITE(self, address, data, write_delay=0):
        payload = bytes([address] + list(data))
        self.device.i2c_write_ex(self.slave_addr, FT4222I2CDevice.FLAG_START_AND_STOP, payload)
        time.sleep(write_delay)

    def GPIO2_WRITE(self, value: bool):
        """控制 OSFP LPMode pin (GPIO2, active-high, 固定 OUTPUT)"""
        self.device.gpio2_write(value)

    def GPIO2_READ(self) -> bool:
        return self.device.gpio2_read()

    def GPIO3_SET_DIRECTION(self, direction):
        """切換 GPIO3 方向：DIR_OUTPUT 驅動 Reset(active-low) / DIR_INPUT
        讀取 IntL —— 依 OSFP 規範這兩個功能複用同一根實體腳位。"""
        self.device.gpio3_set_direction(direction)

    def GPIO3_WRITE(self, value: bool):
        """控制 OSFP Reset pin (GPIO3, active-low)，呼叫前須先
        GPIO3_SET_DIRECTION(DIR_OUTPUT)"""
        self.device.gpio3_write(value)

    def GPIO3_READ(self) -> bool:
        """讀取 OSFP IntL pin，呼叫前須先 GPIO3_SET_DIRECTION(DIR_INPUT)
        （預設值，通常不用手動切）"""
        return self.device.gpio3_read()

    def close(self):
        self.device.close()
