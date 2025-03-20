# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
#
# SPDX-License-Identifier: MIT

package(
    "driver",
    (
        "__init__.py",
        "atecc608b_tngtls/__init__.py",
        "atecc608b_tngtls/atecc_asn1.py",
        "atecc608b_tngtls/atecc_cert_util.py",
        "atecc608b_tngtls/atecc.py",
        "es8311/__init__.py",
        "es8311/reg.py",
        "fpc1020a/fpc1020a/__init__.py",
        "fpc1020a/fpc1020a/api.py",
        "fpc1020a/fpc1020a/types.py",
        "ir/__init__.py",
        "ir/nec.py",
        "ir/receiver.py",
        "ir/transmitter.py",
        "jrd4035/__init__.py",
        "mcp2515/__init__.py",
        "mcp2515/mcp2515_spi.py",
        "mcp2515/mcp2515_param.py",
        "mcp2515/can_frame.py",
        "mfrc522/__init__.py",
        "mfrc522/cmd.py",
        "mfrc522/firmware.py",
        "mfrc522/reg.py",
        "modbus/master/__init__.py",
        "modbus/master/uConst.py",
        "modbus/master/uFunctions.py",
        "modbus/master/uSerial.py",
        "neopixel/__init__.py",
        "neopixel/sk6812.py",
        "neopixel/ws2812.py",
        "rotary/__init__.py",
        "rotary/rotary_irq_esp.py",
        "rotary/rotary.py",
        "simcom/__init__.py",
        "simcom/common.py",
        "simcom/sim7020.py",
        "simcom/sim7028.py",
        "simcom/sim7080.py",
        "ads1110.py",
        "ads1100.py",
        "adxl34x.py",
        "atgm336h.py",
        "aw9523.py",
        "asr650x.py",
        "bh1750.py",
        "bh1750fvi.py",
        "bme68x.py",
        "bmi270_bmm150.py",
        "bmp280.py",
        "button.py",
        "checksum.py",
        "dht12.py",
        "dmx512.py",
        "drf1609h.py",
        "haptic.py",
        "ina226.py",
        "max3421e.py",
        "mcp4725.py",
        "mlx90614.py",
        "pca9554.py",
        "pcf8563.py",
        "qmp6988.py",
        "rui3.py",
        "sam2695.py",
        "scd40_async.py",
        "scd40.py",
        "sen55.py",
        "sgp30.py",
        "sh1107.py",
        "sht4x.py",
        "sht20.py",
        "sht30.py",
        "soft_timer.py",
        "sths34pf80.py",
        "tcs3472.py",
        "timer_thread.py",
        "vl53l0x.py",
        "paj7620.py",
        "mlx90640.py",
        "mpu6886.py",
        "timezone.py",
        "vl53l1x.py",
        "pca9685.py",
    ),
    base_path="..",
    opt=0,
)
