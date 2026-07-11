#!/usr/bin/env python
# -*- coding: utf-8 -*-

##########################
#         Import         #
##########################
import time
from usb_iss import UsbIss

from .i2c_base import I2CDeviceBase

# Define #
USB_ISS_Write_delay = 0.01 # SPEC = 80ms in 8 bytes.
USB_ISS_Read_delay = 0.002

##########################
#         Class          #
##########################
class I2C_ISS(I2CDeviceBase):
    """
        self.port : ex. "COM1"\n
        self.Slave_Addr : Input slave address(8-bit Address).\n
        self.print_debug : Print log = 1; Not to print log = 0; \n
        """
    def __init__(self, port, print_debug = 0, Slave_Addr = 0xA0, speed = 400):
        # Instance Attribute
        self.port = port
        # 7bit Address
        self.Slave_Addr = (Slave_Addr >> 1)
        self.print_debug = print_debug
        self.speed = speed

        self.iss = UsbIss()
        self.iss.open(self.port)
        self.iss.setup_i2c(self.speed)
        #print ("[Interface] Open ") + self.port + "\n"

    def close(self):
        self.iss.close()

    # Basic Function
    def I2C_READ(self, address, number):
        """
        USB-ISS Read
        # byte must be in range(0, 256)
        """
        data = [0]*number
        start = 0
        end = 0
        while(number > 0):
            if number < 60:
                end += number
                #if self.print_debug == 1:
                    #print "start = ", start, "end = ", end, "address = ", address, "number = ", number
                data[start:end] = self.iss.i2c.read(self.Slave_Addr, address, number)
                break
            else:
                end += 60
                #if self.print_debug == 1:
                    #print "start = ", start, "end = ", end, "address = ", address, "number = ", number
                data[start:end] = self.iss.i2c.read(self.Slave_Addr, address, 60)
                start += 60
                address += 60
                if((number - 60) >= 0):
                    number -= 60
                if(address >= 256):
                    address -= 128

        if self.print_debug == 1:
            print ("Read byte 0x%02X value = " %address + str.join("", ("0x%02X, " %a for a in data[0:end])))
        return data

    def I2C_CURRENT_READ(self, number):
        data = [0]*number
        start = 0
        end = 0
        address = 0
        while(number > 0):
            if number < 60:
                end += number
                #if self.print_debug == 1:
                    #print "start = ", start, "end = ", end, "address = ", address, "number = ", number
                data[start:end] = self.iss.i2c.read_ad0(self.Slave_Addr, number)
                break
            else:
                end += 60
                #if self.print_debug == 1:
                    #print "start = ", start, "end = ", end, "address = ", address, "number = ", number
                data[start:end] = self.iss.i2c.read_ad0(self.Slave_Addr, 60)
                start += 60
                address += 60
                if((number - 60) >= 0):
                    number -= 60
                if(address >= 256):
                    address -= 128
        return data

    def I2C_WRITE(self, byte, data, write_delay = USB_ISS_Write_delay):
        """
        USB-ISS Write
        """
        ret = 0
        byte_shift = 0
        Start_address = byte
        number_of_byte = len(data)
        # Modify by Lance
        while(1):
            if number_of_byte > 60:
                ret = self.iss.i2c.write(self.Slave_Addr, Start_address, data[(0 + byte_shift):(60 + byte_shift)])
                Start_address += 60
                number_of_byte -= 60
                byte_shift += 60
            else:
                ret = self.iss.i2c.write(self.Slave_Addr, Start_address, data[byte_shift:(byte_shift + number_of_byte)])
                break
        # Modify by Lance
        time.sleep(write_delay)
        if self.print_debug == 1:
            if byte == 0x7F:
                print ("Page select = " + str.join("", ("0x%02X, " %a for a in data)))
            else:
                print ("Write byte 0x%02X value = " %byte + str.join("", ("0x%02X, " %a for a in data)))
        return ret

    # Addictional Function
    def I2C_PAGE_SELECT(self, page, write_delay = USB_ISS_Write_delay):
        data = [0xFF]
        self.I2C_WRITE(0x7F, page, write_delay)
        time.sleep(write_delay)
        data = self.I2C_READ(0x7F, 1)
        if data != page:
            print ("Change Page %s Fail" %hex(data[0]))
