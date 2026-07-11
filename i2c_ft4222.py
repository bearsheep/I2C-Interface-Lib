import time

from i2c_base import I2CDeviceBase
from ft4222_device import FT4222I2CDevice


class I2C_FT4222(I2CDeviceBase):
    """
        self.slave_addr : Input slave address(8-bit Address).\n
        self.print_debug : Print log = 1; Not to print log = 0; \n
        """
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

    def close(self):
        self.device.close()
