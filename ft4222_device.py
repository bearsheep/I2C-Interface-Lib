import ft4222
import ft4222.I2CMaster as I2CMaster

class FT4222I2CDevice:
    # I2CMaster Flag 常數，讓外部呼叫者不需要直接 import ft4222
    FLAG_START          = I2CMaster.Flag.START
    FLAG_STOP           = I2CMaster.Flag.STOP
    FLAG_START_AND_STOP = I2CMaster.Flag.START_AND_STOP

    def __init__(self, description="FT4222 A", read_timeout=1000, write_timeout=1000):
        self.description = description
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.handle = None

    @staticmethod
    def list_devices():
        """列出所有已連接的 FT4222 設備資訊（description/serial 統一轉為 str）"""
        try:
            dev_count = ft4222.createDeviceInfoList()
            devices = []
            for i in range(dev_count):
                info = ft4222.getDeviceInfoDetail(i)
                # description / serial 可能是 bytes，統一 decode 為 str
                if isinstance(info.get('description'), bytes):
                    info['description'] = info['description'].decode('utf-8', errors='replace').rstrip('\x00')
                if isinstance(info.get('serial'), bytes):
                    info['serial'] = info['serial'].decode('utf-8', errors='replace').rstrip('\x00')
                devices.append(info)
            return devices
        except Exception as e:
            print(f"[FT4222] 列出設備失敗: {e}")
            return []

    def connect(self, speed_khz=1000):
        """
        初始化 FT4222 並設定為 I2C 主機模式
        speed_khz: I2C 速率，預設為 1000 (1MHz)，可設定為 400 (400kHz) 或 100 (100kHz)
        """
        # 1. 確保有偵測到設備
        devices = self.list_devices()
        if not devices:
            raise Exception("未偵測到任何 FT4222 設備！")

        # 2. 開啟指定 Description 的設備
        self.handle = ft4222.openByDescription(self.description)

        # 3. 設定讀寫超時時間（以毫秒為單位），防止 I2C 匯流排異常時主機無限掛起
        self.handle.setTimeouts(self.read_timeout, self.write_timeout)

        # 4. 初始化 I2C 主機模式 (1000 kHz = Fast Mode Plus, 400 kHz = Fast Mode, 100 kHz = Standard Mode)
        self.handle.i2cMaster_Init(speed_khz)

        print(f"[FT4222] 成功連接設備: '{self.description}'，I2C 速率已配置為: {speed_khz} kHz")
        return self.handle

    # ==================== I2C 讀寫封裝 ====================

    def i2c_write(self, slave_addr, data: bytes):
        """I2C 寫入（完整 START-STOP 交易）"""
        if not self.handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        self.handle.i2cMaster_Write(slave_addr, data)

    def i2c_read(self, slave_addr, length: int) -> bytes:
        """I2C 讀取（完整 START-STOP 交易）"""
        if not self.handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        return self.handle.i2cMaster_Read(slave_addr, length)

    def i2c_write_ex(self, slave_addr, flag, data: bytes):
        """I2C 帶旗標寫入（可控制 START/STOP）
        flag: FT4222I2CDevice.FLAG_START / FLAG_STOP / FLAG_START_AND_STOP
        """
        if not self.handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        self.handle.i2cMaster_WriteEx(slave_addr, flag, data)

    def i2c_read_ex(self, slave_addr, flag, length: int) -> bytes:
        """I2C 帶旗標讀取（可控制 START/STOP）
        flag: FT4222I2CDevice.FLAG_START / FLAG_STOP / FLAG_START_AND_STOP
        """
        if not self.handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        return self.handle.i2cMaster_ReadEx(slave_addr, flag, length)

    def close(self):
        if self.handle:
            try:
                self.handle.close()
                print(f"[FT4222] 已成功關閉與 '{self.description}' 的連接。")
            except Exception as e:
                print(f"[FT4222] 關閉連接時發生異常: {e}")
            finally:
                self.handle = None
