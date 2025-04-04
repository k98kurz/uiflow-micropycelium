# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
#
# SPDX-License-Identifier: MIT

from machine import I2C
import time
import struct


class SCD40:
    SCD40_I2C_ADDR = 0x62

    _SCD40_REINIT = 0x3646
    _SCD40_FACTORYRESET = 0x3632
    _SCD40_FORCEDRECAL = 0x362F
    _SCD40_SELFTEST = 0x3639
    _SCD40_DATAREADY = 0xE4B8
    _SCD40_STARTPERIODICMEASUREMENT = 0x21B1
    _SCD40_STOPPERIODICMEASUREMENT = 0x3F86
    _SCD40_STARTLOWPOWERPERIODICMEASUREMENT = 0x21AC
    _SCD40_READMEASUREMENT = 0xEC05
    _SCD40_SERIALNUMBER = 0x3682
    _SCD40_GETTEMPOFFSET = 0x2318
    _SCD40_SETTEMPOFFSET = 0x241D
    _SCD40_GETALTITUDE = 0x2322
    _SCD40_SETALTITUDE = 0x2427
    _SCD40_SETPRESSURE = 0xE000
    _SCD40_PERSISTSETTINGS = 0x3615
    _SCD40_GETASCE = 0x2313
    _SCD40_SETASCE = 0x2416
    _SCD40_SINGLESHOTMEASUREALL = 0x219D
    _SCD40_SINGLESHOTMEASUREHT = 0x2196
    _SCD40_POWERDOWN = 0x36E0
    _SCD40_WAKEUP = 0x36F6

    """"While a periodic measurement is running, no other commands must be issued with the exception of read_measurement(0xec05),get_data_ready_status(0xe4b8), stop_periodic_measurement(0x3f86) and set_ambient_pressure(0xe000)."""

    def __init__(self, i2c: I2C, address: int = SCD40_I2C_ADDR) -> None:
        """! initialize Function
        set I2C Pins, CO2 Address
        """
        self.co2_i2c = i2c
        self.unit_addr = address
        self.available()
        self.co2 = 0
        self.temperature = 0
        self.humidity = 0

    def available(self) -> None:
        """! Is there available or Not? Check."""
        if self.unit_addr not in self.co2_i2c.scan():
            raise Exception("CO2 unit maybe not connect")

    def set_start_periodic_measurement(self) -> None:
        """! set sensor into working mode, about 5s per measurement."""
        try:
            self.write_cmd(self._SCD40_STARTPERIODICMEASUREMENT)
            time.sleep_ms(1)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_stop_periodic_measurement(self) -> None:
        """! stop measurement mode."""
        self.write_cmd(self._SCD40_STOPPERIODICMEASUREMENT)
        time.sleep(0.5)

    def get_sensor_measurement(self) -> None:
        """! get the temp/hum/co2 from the sensor."""
        self.write_cmd(self._SCD40_READMEASUREMENT)
        time.sleep_ms(1)
        buf = self.read_response(9)
        self.co2 = (buf[0] << 8) | buf[1]
        temp = (buf[3] << 8) | buf[1]
        self.temperature = round((-45 + 175 * (temp / (2**16 - 1))), 2)
        humi = (buf[6] << 8) | buf[7]
        self.humidity = round((100 * (humi / (2**16 - 1))), 2)

    def is_data_ready(self) -> bool:
        """! available the temp/hum/co2 from the sensor."""
        if self.data_isready():
            self.get_sensor_measurement()
            return True
        else:
            return False

    def get_temperature_offset(self) -> float:
        """! get the temperature offset to be added to the reported measurements."""
        try:
            self.write_cmd(self._SCD40_GETTEMPOFFSET)
            buf = self.read_response(3)
            temp = (buf[0] << 8) | buf[1]
            time.sleep_ms(1)
            return 175.0 * temp / 2**16
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_temperature_offset(self, offset: int = 0) -> None:
        """! set the maximum value of 374 C temperature offset."""
        try:
            offset = min(374, offset)
            temp = int(offset * (2**16 / 175))
            self.write_cmd(self._SCD40_SETTEMPOFFSET, temp)
            time.sleep_ms(1)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def get_sensor_altitude(self) -> int:
        """! get the altitude value of the measurement location in meters above sea level."""
        try:
            self.write_cmd(self._SCD40_GETALTITUDE)
            time.sleep_ms(1)
            buf = self.read_response(3)
            return (buf[0] << 8) | buf[1]
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_sensor_altitude(self, height: int) -> None:
        """! set the altitude value of the measurement location in meters above sea level."""
        try:
            height = min(65535, max(height, 0))
            self.write_cmd(self._SCD40_SETALTITUDE, int(height))
            time.sleep_ms(1)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_ambient_pressure(self, ambient_pressure: int) -> None:
        """! set the ambient pressure in hPa at any time to adjust CO2 calculations."""
        ambient_pressure = min(65535, max(ambient_pressure, 0))
        self.write_cmd(self._SCD40_SETPRESSURE, int(ambient_pressure))
        time.sleep_ms(1)

    def set_force_calibration(self, target_co2: int) -> None:
        """! set forces the sensor to recalibrate with a given current CO2."""
        try:
            self.set_stop_periodic_measurement()
            self.write_cmd(self._SCD40_FORCEDRECAL, int(target_co2))
            time.sleep(0.5)
            buf = self.read_response(3)
            correction = struct.unpack_from(">h", buf[0:2])[0]
            if correction == 0xFFFF:
                raise RuntimeError(
                    "Forced recalibration failed. Make sure sensor is active for 3 minutes first"
                )
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def get_calibration_enabled(self) -> bool:
        """! get the Enables or disables automatic self calibration (ASC)."""
        try:
            self.write_cmd(self._SCD40_GETASCE)
            time.sleep_ms(1)
            buf = self.read_response(3)
            return buf[1] == 1
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_calibration_enabled(self, enabled: bool) -> None:
        """! set the Enables or disables automatic self calibration (ASC)."""

        try:
            enabled = min(1, max(enabled, 0))
            self.write_cmd(self._SCD40_SETASCE, enabled)
            time.sleep_ms(1)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_start_low_periodic_measurement(self) -> None:
        """! set sensor into low power working mode, about 30s per measurement."""
        try:
            self.write_cmd(self._SCD40_STARTLOWPOWERPERIODICMEASUREMENT)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def data_isready(self) -> bool:
        """! check the sensor if new data is available."""
        self.write_cmd(self._SCD40_DATAREADY)
        time.sleep_ms(1)
        buf = self.read_response(3)
        return not ((buf[0] & 0x07 == 0) and (buf[1] == 0))

    def save_to_eeprom(self) -> None:
        """! save temperature offset, altitude offset, and selfcal enable settings to EEPROM."""
        try:
            self.write_cmd(self._SCD40_PERSISTSETTINGS)
            time.sleep(0.8)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def get_serial_number(self) -> tuple:
        """! get a unique serial number for this sensor."""
        try:
            self.write_cmd(self._SCD40_SERIALNUMBER)
            time.sleep_ms(1)
            buf = self.read_response(9)
            return (buf[0], buf[1], buf[3], buf[4], buf[6], buf[7])
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_self_test(self) -> None:
        """! set a self test, takes up to 10 seconds."""
        try:
            self.set_stop_periodic_measurement()
            self.write_cmd(self._SCD40_SELFTEST)
            time.sleep(10)
            buf = self.read_response(3)
            if (buf[0] != 0) or (buf[1] != 0):
                raise RuntimeError("Self test failed")
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_factory_reset(self) -> None:
        """! resets all configuration settings stored in the EEPROM and erases the FRC and ASC algorithm history."""
        try:
            self.set_stop_periodic_measurement()
            self.write_cmd(self._SCD40_FACTORYRESET)
            time.sleep(1.2)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def reinit(self) -> None:
        """! reinitializes the sensor by reloading user settings from EEPROM."""
        try:
            self.set_stop_periodic_measurement()
            self.write_cmd(self._SCD40_REINIT)
            time.sleep_ms(20)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_single_shot_measurement_all(self) -> None:
        """! set single shot measure in Co2, humidity and temperature."""
        try:
            self.write_cmd(self._SCD40_SINGLESHOTMEASUREALL)
            time.sleep(5)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_single_shot_measurement_ht(self) -> None:
        """! set single shot measure in humidity and temperature."""
        try:
            self.write_cmd(self._SCD40_SINGLESHOTMEASUREHT)
            time.sleep_ms(50)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_sleep_mode(self) -> None:
        """! set power down the sensor from idle to sleep and reduce current consumption."""
        try:
            self.write_cmd(self._SCD40_POWERDOWN)
            time.sleep_ms(1)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def set_wake_up(self) -> None:
        """! set wake up the sensor from sleep mode into idle mode."""
        try:
            self.write_cmd(self._SCD40_WAKEUP)
            time.sleep_ms(20)
        except:
            raise OSError(
                "Indicates that the block cannot be executed while a periodic measurement is running"
            )

    def write_cmd(self, cmd_wr: int, value: int = None) -> None:
        """! write the command of sensor
        cmd_wr : 2 byte value
        value : None or 2 byte value
        """
        if value is not None:
            byte_val = struct.pack(">h", value)
            crc8 = self._crc8(byte_val)
            self.co2_i2c.writeto(self.unit_addr, struct.pack(">hhb", cmd_wr, value, crc8))
        else:
            self.co2_i2c.writeto(self.unit_addr, struct.pack(">h", cmd_wr))

    def read_response(self, num: int) -> bytearray:
        """! read response of sensor
        num : number of byte read
        """
        buff = self.co2_i2c.readfrom(self.unit_addr, num)
        self._check_crc(buff)
        return buff

    def _check_crc(self, buf: bytearray) -> bool:
        """! check the crc
        buf : buffer of bytes
        """
        for i in range(0, len(buf), 3):
            if self._crc8(buf[i : (i + 2)]) != buf[i + 2]:
                raise RuntimeError("CRC check failed while reading data")
        return True

    def _crc8(self, buffer: bytearray) -> int:
        """! crc 8 bits
        buffer : buffer of bytes
        """
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF  # return the bottom 8 bits
