import ft4222
import ft4222.I2CMaster as I2CMaster
import ft4222.GPIO as GPIO

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
        # GPIO2(LPMode)/GPIO3(Reset/IntL，依 OSFP 規範是同一根實體腳位複用)
        # 實測無法跟 I2C master 共用同一個 handle 讀寫（寫入後讀回恆為 0），
        # 必須走晶片另一個邏輯介面（"...B"），詳見 _gpio_description()。
        # gpio_handle 跟 handle 可同時開啟、互不干擾。
        self.gpio_handle = None
        # GPIO0/GPIO1 是這片 UMFT4222EV 板子的 I2C SDA/SCL，不透過 gpio_* 方法
        # 控制，方向固定填 INPUT 只是為了滿足 gpio_Init() 一次要指定全部 4 個
        # port 的介面。GPIO2 固定 OUTPUT（LPMode，host 主動驅動）；GPIO3 依
        # OSFP 規範是 Reset(OUTPUT)/IntL(INPUT) 複用腳位，預設 INPUT，方向可
        # 用 gpio3_set_direction() 切換。
        self._gpio_dir = {
            GPIO.Port.P0: GPIO.Dir.INPUT,
            GPIO.Port.P1: GPIO.Dir.INPUT,
            GPIO.Port.P2: GPIO.Dir.OUTPUT,
            GPIO.Port.P3: GPIO.Dir.INPUT,
        }

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

    def _gpio_description(self):
        """GPIO2/GPIO3 實測必須透過晶片另一個邏輯介面控制（跟 I2C master 用的
        介面不同，例如 'FT4222 A' 對應的 GPIO 介面是 'FT4222 B'）。"""
        if self.description.endswith(' A'):
            return self.description[:-1] + 'B'
        return f'{self.description} B'

    def connect(self, speed_khz=1000):
        """
        初始化 FT4222 並設定為 I2C 主機模式，同時另外開啟 GPIO 專用的第二個邏輯
        介面，初始化 GPIO2(LPMode)/GPIO3(Reset/IntL)。
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

        # 5. GPIO2(LPMode)/GPIO3(Reset) 走另一個邏輯介面（見 _gpio_description）
        self.gpio_handle = ft4222.openByDescription(self._gpio_description())
        self.gpio_handle.setTimeouts(self.read_timeout, self.write_timeout)
        self._gpio_init_osfp_pins()

        print(f"[FT4222] 成功連接設備: '{self.description}'，I2C 速率已配置為: {speed_khz} kHz")
        return self.handle

    def _gpio_init_osfp_pins(self):
        """釋放 GPIO2/GPIO3 的特殊功能，並依 self._gpio_dir 目前狀態（見
        __init__）設定方向：GPIO2 固定 OUTPUT，預設寫入 LOW（LPMode off，
        正常功耗）；GPIO3 預設 INPUT（讀 IntL），若要驅動 Reset 需先呼叫
        gpio3_set_direction(GPIO.Dir.OUTPUT)。
        """
        self.gpio_handle.setSuspendOut(False)       # 釋放 GPIO2，讓它可以當一般 GPIO（LPMode）
        self.gpio_handle.setWakeUpInterrupt(False)  # 釋放 GPIO3，讓它可以當一般 GPIO（Reset/IntL）
        self._gpio_apply_direction()
        self.gpio_handle.gpio_Write(GPIO.Port.P2, False)  # LPMode 預設 LOW（正常功耗，active-high）

    def _gpio_apply_direction(self):
        """底層 gpio_Init() 每次都要求指定全部 4 個 port，這裡依
        self._gpio_dir 目前狀態整批重新呼叫。"""
        self.gpio_handle.gpio_Init(
            gpio0=self._gpio_dir[GPIO.Port.P0],
            gpio1=self._gpio_dir[GPIO.Port.P1],
            gpio2=self._gpio_dir[GPIO.Port.P2],
            gpio3=self._gpio_dir[GPIO.Port.P3],
        )

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

    # ==================== GPIO 讀寫封裝 ====================

    def gpio2_write(self, value: bool):
        """GPIO2 = OSFP LPMode pin (active-high，固定 OUTPUT)"""
        if not self.gpio_handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        self.gpio_handle.gpio_Write(GPIO.Port.P2, value)

    def gpio2_read(self) -> bool:
        """GPIO2 = OSFP LPMode pin (active-high)"""
        if not self.gpio_handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        return self.gpio_handle.gpio_Read(GPIO.Port.P2)

    def gpio3_set_direction(self, direction):
        """切換 GPIO3 方向：GPIO.Dir.OUTPUT 驅動 Reset(active-low) /
        GPIO.Dir.INPUT 讀取 IntL —— 依 OSFP 規範這兩個功能複用同一根實體
        腳位，預設方向是 INPUT（見 _gpio_init_osfp_pins）。
        """
        if not self.gpio_handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        self._gpio_dir[GPIO.Port.P3] = direction
        self._gpio_apply_direction()

    def gpio3_write(self, value: bool):
        """GPIO3 = OSFP Reset pin (active-low)，呼叫前須先
        gpio3_set_direction(GPIO.Dir.OUTPUT)"""
        if not self.gpio_handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        self.gpio_handle.gpio_Write(GPIO.Port.P3, value)

    def gpio3_read(self) -> bool:
        """GPIO3 = OSFP IntL pin，呼叫前須先
        gpio3_set_direction(GPIO.Dir.INPUT)（預設值，通常不用手動切）"""
        if not self.gpio_handle:
            raise RuntimeError("設備未連接，請先呼叫 connect()")
        return self.gpio_handle.gpio_Read(GPIO.Port.P3)

    def close(self):
        if self.handle:
            try:
                self.handle.close()
                print(f"[FT4222] 已成功關閉與 '{self.description}' 的連接。")
            except Exception as e:
                print(f"[FT4222] 關閉連接時發生異常: {e}")
            finally:
                self.handle = None
        if self.gpio_handle:
            try:
                self.gpio_handle.close()
            except Exception as e:
                print(f"[FT4222] 關閉 GPIO 介面時發生異常: {e}")
            finally:
                self.gpio_handle = None
