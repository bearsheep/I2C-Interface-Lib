from abc import ABC, abstractmethod


class I2CDeviceBase(ABC):
    """
    self.port : ex. "COM1"\n
    self.Slave_Addr : Input slave address(8-bit Address).\n
    self.print_debug : Print log = 1; Not to print log = 0; \n
    """

    @abstractmethod
    def I2C_READ(self, address, number):
        ...

    @abstractmethod
    def I2C_WRITE(self, address, data, write_delay=0):
        ...

    def I2C_PAGE_SELECT(self, page, write_delay=0):
        self.I2C_WRITE(0x7F, page, write_delay)
        data = self.I2C_READ(0x7F, 1)
        if data != page:
            print("Change Page %s Fail" % hex(data[0]))

    @abstractmethod
    def close(self):
        ...
