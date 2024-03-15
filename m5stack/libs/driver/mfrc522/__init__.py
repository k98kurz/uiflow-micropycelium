# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
#
# SPDX-License-Identifier: MIT
import time
from .reg import (
    COMMAND_REG,
    COMIRQ_REG,
    DIVIRQ_REG,
    ERROR_REG,
    STATUS2_REG,
    FIFODATA_REG,
    FIFOLEVEL_REG,
    CONTROL_REG,
    BITFRAMING_REG,
    COLL_REG,
    MODE_REG,
    TXCONTROL_REG,
    TXASK_REG,
    CRCRESULT_REGH,
    CRCRESULT_REGL,
    RFCFG_REG,
    TMODE_REG,
    TPRESCALER_REG,
    TRELOAD_REGH,
    TRELOAD_REGL,
    AUTOTEST_REG,
    VERSION_REG,
)
from .cmd import (
    PCD_IDLE,
    PCD_MEM,
    PCD_CALCCRC,
    PCD_TRANSCEIVE,
    PCD_MFAUTHENT,
    PCD_SOFTRESET,
    PICC_CMD_REQA,
    PICC_CMD_WUPA,
    PICC_CMD_CT,
    PICC_CMD_SEL_CL1,
    PICC_CMD_SEL_CL2,
    PICC_CMD_SEL_CL3,
    PICC_CMD_HLTA,
    PICC_CMD_MF_AUTH_KEY_A,
    PICC_CMD_MF_AUTH_KEY_B,
    PICC_CMD_MF_READ,
    PICC_CMD_MF_WRITE,
    PICC_CMD_MF_DECREMENT,
    PICC_CMD_MF_INCREMENT,
    PICC_CMD_MF_RESTORE,
    PICC_CMD_UL_WRITE,
)

from .firmware import (
    FM17522_firmware_reference,
    MFRC522_firmware_referenceV0_0,
    MFRC522_firmware_referenceV1_0,
    MFRC522_firmware_referenceV2_0,
)


class UID:
    uid = bytearray(10)
    sak = 0

    def __len__(self):
        return self.size

    def __getitem__(self, index):
        return self.uid[index]

    def __setitem__(self, key, value):
        self.uid[key] = value

    def __delitem__(self, key):
        del self.uid[key]

    def __str__(self):
        print(self.uid.hex())


class MFRC522:
    ## Return codes from the functions in this class.
    #  Remember to update GetStatusCodeName() if you add more.
    STATUS_OK = 1  # Success
    STATUS_ERROR = 2  # Error in communication
    STATUS_COLLISION = 3  # Collission detected
    STATUS_TIMEOUT = 4  # Timeout in communication.
    STATUS_NO_ROOM = 5  # A buffer is not big enough.
    STATUS_INTERNAL_ERROR = 6  # Internal error in the code. Should not happen ;-)
    STATUS_INVALID = 7  # Invalid argument.
    STATUS_CRC_WRONG = 8  # The CRC_A does not match
    STATUS_MIFARE_NACK = 9  # A MIFARE PICC responded with NAK.

    # PICC types we can detect. Remember to update picc_get_type_name() if you add more.
    PICC_TYPE_UNKNOWN = 0
    PICC_TYPE_ISO_14443_4 = 1  # PICC compliant with ISO/IEC 14443-4
    PICC_TYPE_ISO_18092 = 2  # PICC compliant with ISO/IEC 18092 (NFC)
    PICC_TYPE_MIFARE_MINI = 3  # MIFARE Classic protocol, 320 bytes
    PICC_TYPE_MIFARE_1K = 4  # MIFARE Classic protocol, 1KB
    PICC_TYPE_MIFARE_4K = 5  # MIFARE Classic protocol, 4KB
    PICC_TYPE_MIFARE_UL = 6  # MIFARE Ultralight or Ultralight C
    PICC_TYPE_MIFARE_PLUS = 7  # MIFARE Plus
    PICC_TYPE_TNP3XXX = 8  # Only mentioned in NXP AN 10833 MIFARE Type Identification Procedure
    PICC_TYPE_NOT_COMPLETE = 255  # SAK indicates UID is not complete.

    def __init__(self, i2c, addr) -> None:
        self._i2c = i2c
        self._addr = addr

        self._uid = UID()

        self._CRC_BUFFER = memoryview(bytearray(2))
        self._BUFFER1 = memoryview(bytearray(1))
        self._BUFFER2 = memoryview(bytearray(2))
        self._BUFFER4 = memoryview(bytearray(4))
        self._BUFFER12 = memoryview(bytearray(12))
        self._BUFFER18 = memoryview(bytearray(18))

    ## Initializes the MFRC522 chip.
    #
    #  @param self The object pointer.
    def pcd_init(self):
        self.pcd_reset()

        # When communicating with a PICC we need a timeout if something goes wrong.
        # f_timer = 13.56 MHz / (2*TPreScaler+1) where TPreScaler = [TPrescaler_Hi:TPrescaler_Lo].
        # TPrescaler_Hi are the four low bits in TModeReg. TPrescaler_Lo is TPrescalerReg.

        # TAuto=1; timer starts automatically at the end of the transmission in
        # all communication modes at all speeds
        self.pcd_write_register(TMODE_REG, 0x80)
        # TPreScaler = TModeReg[3..0]:TPrescalerReg,
        # ie 0x0A9 = 169 => f_timer=40kHz, ie a timer period of 25ms.
        self.pcd_write_register(TPRESCALER_REG, 0xA9)
        # Reload timer with 0x3E8 = 1000, ie 25ms before timeout.
        self.pcd_write_register(TRELOAD_REGH, 0x03)
        self.pcd_write_register(TRELOAD_REGL, 0xE8)

        # Default 0x00. Force a 100 % ASK modulation independent of the
        # ModGsPReg register setting
        self.pcd_write_register(TXASK_REG, 0x40)
        # Default 0x3F. Set the preset value for the CRC coprocessor for the
        # CalcCRC command to 0x6363 (ISO 14443-3 part 6.2.4)
        self.pcd_write_register(MODE_REG, 0x3D)

        # Enable the antenna driver pins TX1 and TX2 (they were disabled by the
        # reset)
        self.pcd_antenna_on()

    ## Performs a soft reset on the MFRC522 chip and waits for it to be ready again.
    #
    #  @param self The object pointer.
    def pcd_reset(self):
        # Issue the SoftReset command.
        self.pcd_write_register(COMMAND_REG, PCD_SOFTRESET)
        time.sleep_ms(50)
        # Wait for the PowerDown bit in CommandReg to be cleared
        while self.pcd_read_register(COMMAND_REG) & (1 << 4):
            # PCD still restarting - unlikely after waiting 50ms, but better
            # safe than sorry.
            pass

    ## Turns the antenna on by enabling pins TX1 and TX2.
    #
    #  After a reset these pins are disabled.
    #
    #  @param self The object pointer.
    def pcd_antenna_on(self):
        value = self.pcd_read_register(TXCONTROL_REG)
        if (value & 0x03) != 0x03:
            self.pcd_write_register(TXCONTROL_REG, value | 0x03)

    def pcd_antenna_off(self):
        """Turns the antenna off by disabling pins TX1 and TX2."""
        self.pcd_clear_register_bitmask(TXCONTROL_REG, 0x03)

    def pcd_get_antenna_gain(self):
        """Get the current MFRC522 Receiver Gain (RxGain[2:0]) value.
        See 9.3.3.6 / table 98 in http://www.nxp.com/documents/data_sheet/MFRC522.pdf
        NOTE: Return value scrubbed with (0x07<<4)=01110000b as RCFfgReg may use
              reserved bits.

        return Value of the RxGain, scrubbed to the 3 bits used.
        """
        return self.pcd_read_register(RFCFG_REG) & (0x07 << 4)

    def pcd_set_antenna_gain(self, mask):
        """Set the MFRC522 Receiver Gain (RxGain) to value specified by given mask.
        See 9.3.3.6 / table 98 in http://www.nxp.com/documents/data_sheet/MFRC522.pdf
        NOTE: Given mask is scrubbed with (0x07<<4)=01110000b as RCFfgReg may
              use reserved bits.
        """
        # only bother if there is a change
        if self.pcd_get_antenna_gain() != mask:
            # clear needed to allow 000 pattern
            self.pcd_clear_register_bitmask(RFCFG_REG, (0x07 << 4))
            # only set RxGain[2:0] bits
            self.pcd_set_register_bitmask(RFCFG_REG, mask & (0x07 << 4))

    def pcd_write_register(self, reg, val):
        # print("Write: Reg 0x{:02X}, Value: {:#02X}".format(reg, val))
        self._i2c.writeto_mem(self._addr, reg, bytes([val]))

    def pcd_read_register(self, reg):
        val = self._i2c.readfrom_mem(self._addr, reg, 1)
        # print("Read: Reg 0x{:02X}, Value: {:#02X}".format(reg, val[0]))
        return val[0]

    def pcd_set_register_bitmask(self, reg, mask):
        tmp = self.pcd_read_register(reg)
        self.pcd_write_register(reg, tmp | mask)

    def pcd_clear_register_bitmask(self, reg, mask):
        tmp = self.pcd_read_register(reg)
        self.pcd_write_register(reg, tmp & (~mask))

    def pcd_perform_self_test(self):
        """Performs a self-test of the MFRC522
        See 16.1.1 in http://www.nxp.com/documents/data_sheet/MFRC522.pdf

        @return Whether or not the test passed.
        """
        # This follows directly the steps outlined in 16.1.1
        # 1. Perform a soft reset.
        self.pcd_reset()

        # 2. Clear the internal buffer by writing 25 bytes of 00h
        ZEROES = bytearray(25)
        # flush the FIFO buffer
        self.pcd_set_register_bitmask(FIFOLEVEL_REG, 0x80)
        # write 25 bytes of 00h to FIFO
        self.pcd_write_bytes(FIFODATA_REG, ZEROES)
        # transfer to internal buffer
        self.pcd_write_register(COMMAND_REG, PCD_MEM)

        # 3. Enable self-test
        self.pcd_write_register(AUTOTEST_REG, 0x09)

        # 4. Write 00h to FIFO buffer
        self.pcd_write_register(FIFODATA_REG, 0x00)

        # 5. Start self-test by issuing the CalcCRC command
        self.pcd_write_register(COMMAND_REG, PCD_CALCCRC)

        # 6. Wait for self-test to complete
        for i in range(0xFF):
            # DivIrqReg[7..0] bits are: Set2 reserved reserved MfinActIRq
            # reserved CRCIRq reserved reserved
            n = self.pcd_read_register(DIVIRQ_REG)
            if n & 0x04:
                # CRCIRq bit set - calculation done
                break

        # Stop calculating CRC for new content in the FIFO.
        self.pcd_write_register(COMMAND_REG, PCD_IDLE)

        # 7. Read out resulting 64 bytes from the FIFO buffer.
        result = bytearray(64)
        self.pcd_read_bytes(FIFODATA_REG, result, 0)

        # Auto self-test done
        # Reset AutoTestReg register to be 0 again. Required for normal operation.
        self.pcd_write_register(AUTOTEST_REG, 0x00)

        # Determine firmware version (see section 9.3.4.8 in spec)
        version = self.pcd_read_register(VERSION_REG)

        # Pick the appropriate reference values
        reference = {
            0x88: FM17522_firmware_reference,
            0x90: MFRC522_firmware_referenceV0_0,
            0x91: MFRC522_firmware_referenceV1_0,
            0x92: MFRC522_firmware_referenceV2_0,
        }.get(version, None)

        if not reference:
            return False

        # Verify that the results match up to our expectations
        for i in range(64):
            if result[i] != reference[i]:
                return False

        # Test passed; all is good.
        return True

    def pcd_transceive_data(self, sendData: bytearray, validBits=None, rxAlign=0, checkCRC=False):
        """Executes the Transceive command.
        CRC validation can only be done if backData and backLen are specified.

        @return STATUS_OK on success, STATUS_??? otherwise.
        """
        return self.pcd_communicate_with_picc(
            PCD_TRANSCEIVE,
            0x30,
            sendData,
            validBits=validBits,
            rxAlign=rxAlign,
            checkCRC=checkCRC,
        )

    def pcd_communicate_with_picc(
        self, command, waitIRq, sendData, validBits=None, rxAlign=0, checkCRC=False
    ):
        _validBits = 0

        txLastBits = validBits if validBits is not None else 0
        bitFraming = (rxAlign << 4) + txLastBits

        self.pcd_write_register(COMMAND_REG, PCD_IDLE)
        self.pcd_write_register(COMIRQ_REG, 0x7F)
        self.pcd_set_register_bitmask(FIFOLEVEL_REG, 0x80)
        self.pcd_write_bytes(FIFODATA_REG, sendData)
        self.pcd_write_register(BITFRAMING_REG, bitFraming)
        self.pcd_write_register(COMMAND_REG, command)

        if command == PCD_TRANSCEIVE:
            self.pcd_set_register_bitmask(BITFRAMING_REG, 0x80)

        # Wait for the command to complete.
        # In PCD_Init() we set the TAuto flag in TModeReg. This means the timer
        # automatically starts when the PCD stops transmitting.
        last_ticks_us = time.ticks_us()
        while True:
            # ComIrqReg[7..0] bits are:
            #     Set1 TxIRq RxIRq IdleIRq HiAlertIRq LoAlertIRq ErrIRq TimerIRq
            n = self.pcd_read_register(COMIRQ_REG)
            if n & waitIRq:
                # One of the interrupts that signal success has been set.
                break
            if n & 0x01:
                # Timer interrupt - nothing received in 25ms
                return (self.STATUS_TIMEOUT, None, validBits)
            if time.ticks_us() - last_ticks_us >= 37500:
                # The emergency break. If all other condions fail we will
                # eventually terminate on this one after 35.7ms. Communication
                # with the MFRC522 might be down.
                return (self.STATUS_TIMEOUT, None, validBits)

        errorRegValue = self.pcd_read_register(ERROR_REG)
        # print("errorRegValue:", errorRegValue)
        if errorRegValue & 0x13:
            return (self.STATUS_ERROR, None, validBits)

        backData = None
        l = self.pcd_read_register(FIFOLEVEL_REG)
        if l > 0:
            backData = bytearray(l)
            self.pcd_read_bytes(FIFODATA_REG, backData, rxAlign)
            _validBits = self.pcd_read_register(CONTROL_REG) & 0x07
            if validBits is not None:
                validBits = _validBits

        # print("backData:", backData)

        if errorRegValue & 0x08:
            return (self.STATUS_COLLISION, backData, validBits)

        if backData and checkCRC:
            if len(backData) == 1 and _validBits == 4:
                return (self.STATUS_MIFARE_NACK, backData, validBits)
            if len(backData) < 2 or _validBits != 0:
                return (self.STATUS_CRC_WRONG, backData, validBits)
            status = self.pcd_calculate_crc(backData[:-2], self._CRC_BUFFER)
            if status != self.STATUS_OK:
                return (status, backData, validBits)
            if (backData[-2] != self._CRC_BUFFER[0]) or (backData[-1] != self._CRC_BUFFER[1]):
                return (self.STATUS_CRC_WRONG, backData, validBits)

        return (self.STATUS_OK, backData, validBits)

    """Functions for communicating with PICCs"""

    def picc_request_a(self, bufferATQA):
        return self.picc_reqa_or_wupa(PICC_CMD_REQA, bufferATQA)

    def picc_wakeup_a(self, bufferATQA):
        return self.picc_reqa_or_wupa(PICC_CMD_WUPA, bufferATQA)

    def picc_reqa_or_wupa(self, command, bufferATQA):
        if bufferATQA is None or len(bufferATQA) < 2:
            return self.STATUS_NO_ROOM

        self.pcd_clear_register_bitmask(COLL_REG, 0x80)
        validBits = 7
        self._BUFFER1[0] = command
        status, responseBuffer, validBits = self.pcd_transceive_data(
            self._BUFFER1, validBits=validBits
        )
        if responseBuffer:
            bufferATQA[0 : len(responseBuffer)] = responseBuffer

        if status != self.STATUS_OK:
            return status

        if len(bufferATQA) != 2 or validBits != 0:
            return self.STATUS_ERROR

        return self.STATUS_OK

    def picc_select(self, uid, validBits=0):
        """Transmits SELECT/ANTICOLLISION commands to select a single PICC.
        Before calling this function the PICCs must be placed in the READY(*) state by calling picc_request_a() or picc_wakeup_a().
        On success:
            - The chosen PICC is in state ACTIVE(*) and all other PICCs have returned to state IDLE/HALT. (Figure 7 of the ISO/IEC 14443-3 draft.)
            - The UID size and value of the chosen PICC is returned in *uid along with the SAK.

        A PICC UID consists of 4, 7 or 10 bytes.
        Only 4 bytes can be specified in a SELECT command, so for the longer UIDs two or three iterations are used:
            UID size    Number of UID bytes    Cascade levels    Example of PICC
            ========    ===================    ==============    ===============
            single                        4                 1    MIFARE Classic
            double                        7                 2    MIFARE Ultralight
            triple                       10                 3    Not currently in use?

            @return STATUS_OK on success, STATUS_??? otherwise.
        """
        uidComplete = False
        selectDone = False
        useCascadeTag = False
        cascadeLevel = 1
        result = 0
        count = 0
        index = 0
        uidIndex = 0
        currentLevelKnownBits = 0
        buffer = memoryview(bytearray(9))
        bufferUsed = 0
        rxAlign = 0
        txLastBits = 0
        responseBuffer = None

        # Sanity checks
        if validBits > 80:
            return self.STATUS_INVALID

        # Prepare MFRC522
        # ValuesAfterColl=1 => Bits received after collision are cleared.
        self.pcd_clear_register_bitmask(COLL_REG, 0x80)

        # Repeat Cascade Level loop until we have a complete UID.
        while not uidComplete:
            # Set the Cascade Level in the SEL uint8_t, find out if we need to use the Cascade Tag in uint8_t 2.
            if cascadeLevel == 1:
                buffer[0] = PICC_CMD_SEL_CL1
                uidIndex = 0
                # When we know that the UID has more than 4 bytes
                useCascadeTag = validBits and len(uid) > 4
            elif cascadeLevel == 2:
                buffer[0] = PICC_CMD_SEL_CL2
                uidIndex = 3
                # When we know that the UID has more than 7 bytes
                useCascadeTag = validBits and len(uid) > 7
            elif cascadeLevel == 3:
                buffer[0] = PICC_CMD_SEL_CL3
                uidIndex = 6
                # Never used in CL3.
                useCascadeTag = False
            else:
                return self.STATUS_INTERNAL_ERROR

            # How many UID bits are known in this Cascade Level?
            currentLevelKnownBits = validBits - (8 * uidIndex)
            if currentLevelKnownBits < 0:
                currentLevelKnownBits = 0

            # Copy the known bits from uid->uidByte[] to buffer[]
            # destination index in buffer[]
            index = 2
            if useCascadeTag:
                buffer[index] = PICC_CMD_CT
                index += 1

            # The number of bytes needed to represent the known bits for this level.
            bytesToCopy = currentLevelKnownBits // 8 + (1 if currentLevelKnownBits % 8 else 0)
            if bytesToCopy:
                # Max 4 bytes in each Cascade Level. Only 3 left if we use the Cascade Tag
                maxBytes = 3 if useCascadeTag else 4
                if bytesToCopy > maxBytes:
                    bytesToCopy = maxBytes
                # for count in range(bytesToCopy):
                #     buffer[index + count] = uid[uidIndex + count]
                buffer[index : index + bytesToCopy] = uid[uidIndex : uidIndex + bytesToCopy]

            # Now that the data has been copied we need to include the 8 bits in
            # CT in currentLevelKnownBits
            if useCascadeTag:
                currentLevelKnownBits += 8

            # Repeat anti collision loop until we can transmit all
            # UID bits + BCC and receive a SAK - max 32 iterations.
            selectDone = False
            while not selectDone:
                if currentLevelKnownBits >= 32:
                    buffer[1] = 0x70
                    buffer[6] = buffer[2] ^ buffer[3] ^ buffer[4] ^ buffer[5]
                    status = self.pcd_calculate_crc(buffer[0:7], buffer[7:9])
                    # print("pcd_calculate_crc() status:", status)
                    if status != self.STATUS_OK:
                        return status
                    txLastBits = 0
                    bufferUsed = 9
                    responseBuffer = buffer[6:]
                else:
                    txLastBits = currentLevelKnownBits % 8
                    count = currentLevelKnownBits // 8
                    index = 2 + count
                    buffer[1] = (index << 4) + txLastBits
                    bufferUsed = index + (1 if txLastBits else 0)
                    responseBuffer = buffer[index:]

                # Set bit adjustments
                # Having a seperate variable is overkill. But it makes the next
                # line easier to read.
                rxAlign = txLastBits
                # RxAlign = BitFramingReg[6..4]. TxLastBits = BitFramingReg[2..0]
                self.pcd_write_register(BITFRAMING_REG, (rxAlign << 4) + txLastBits)

                # Transmit the buffer and receive the response.
                status, responseBuffer1, txLastBits = self.pcd_transceive_data(
                    buffer[:bufferUsed],
                    validBits=txLastBits,
                    rxAlign=rxAlign,
                )
                if responseBuffer1:
                    responseBuffer[0 : len(responseBuffer1)] = responseBuffer1

                if status == self.STATUS_COLLISION:
                    # More than one PICC in the field => collision.

                    # CollReg[7..0] bits are: ValuesAfterColl reserved
                    # CollPosNotValid CollPos[4:0]
                    result = self.pcd_read_register(COLL_REG)
                    if result & 0x20:
                        # CollPosNotValid

                        # Without a valid collision position we cannot continue
                        return self.STATUS_COLLISION

                    # Values 0-31, 0 means bit 32.
                    collisionPos = result & 0x1F
                    collisionPos = 32 if collisionPos == 0 else collisionPos

                    if collisionPos <= currentLevelKnownBits:
                        # No progress - should not happen
                        return self.STATUS_INTERNAL_ERROR

                    # Choose the PICC with the bit set.
                    currentLevelKnownBits = collisionPos
                    # The bit to modify
                    count = (currentLevelKnownBits - 1) % 8
                    # First uint8_t is index 0.
                    index = 1 + (currentLevelKnownBits // 8) + (1 if count else 0)
                    buffer[index] |= 1 << count
                elif status != self.STATUS_OK:
                    return status
                else:
                    if currentLevelKnownBits >= 32:
                        # This was a SELECT.

                        # No more anticollision We continue below outside the
                        # while.
                        selectDone = True
                    else:
                        # This was an ANTICOLLISION.

                        # We now have all 32 bits of the UID in this Cascade Level
                        currentLevelKnownBits = 32
                        # Run loop again to do the SELECT.

            # We do not check the CBB - it was constructed by us above.
            # Copy the found UID bytes from buffer[] to uid->uidByte[]
            index = 3 if (buffer[2] == PICC_CMD_CT) else 2  # source index in buffer[]
            bytesToCopy = 3 if (buffer[2] == PICC_CMD_CT) else 4
            for count in range(bytesToCopy):
                self._uid.uid[uidIndex + count] = buffer[index]
                index += 1
            # self._uid.uid[uidIndex : uidIndex + bytesToCopy] = buffer[:bytesToCopy]

            # Check response SAK (Select Acknowledge)
            # SAK must be exactly 24 bits (1 uint8_t + CRC_A).
            if len(responseBuffer) != 3 or txLastBits != 0:
                return self.STATUS_ERROR

            # Verify CRC_A - do our own calculation and store the control in buffer[2..3] - those bytes are not needed anymore.
            result = self.pcd_calculate_crc(responseBuffer[0:1], buffer[2:4])
            if result != self.STATUS_OK:
                return result

            if (buffer[2] != responseBuffer[1]) or (buffer[3] != responseBuffer[2]):
                return self.STATUS_CRC_WRONG

            if responseBuffer[0] & 0x04:  # Cascade bit set - UID not complete yes
                cascadeLevel += 1
            else:
                uidComplete = True
                self._uid.sak = responseBuffer[0]

        return self.STATUS_OK

    def picc_halt_a(self):
        # Build command buffer
        self._BUFFER4[0] = PICC_CMD_HLTA
        self._BUFFER4[1] = 0
        # Calculate CRC_A
        status = self.pcd_calculate_crc(self._BUFFER4[0:2], self._BUFFER4[2:4])
        if status != self.STATUS_OK:
            return status

        # Send the command.
        # The standard says:
        #    If the PICC responds with any modulation during a period of 1 ms after the end of the frame containing the
        #    HLTA command, this response shall be interpreted as 'not acknowledge'.
        # We interpret that this way: Only STATUS_TIMEOUT is a success.
        status, _, _ = self.pcd_transceive_data(self._BUFFER4)
        if status == self.STATUS_TIMEOUT:
            return self.STATUS_OK
        if status == self.STATUS_OK:  # That is ironically NOT ok in this case ;-)
            return self.STATUS_ERROR
        return status

    """Functions for communicating with MIFARE PICCs"""

    def pcd_authenticate(self, command, blockAddr, key, uid: UID):
        waitIRq = 0x10  # IdleIRq

        # Build command buffer
        self._BUFFER12[0] = command
        self._BUFFER12[1] = blockAddr
        self._BUFFER12[2 : 2 + len(key)] = key
        self._BUFFER12[8:12] = uid.uid[:4]

        # Start the authentication.
        status, _, _ = self.pcd_communicate_with_picc(PCD_MFAUTHENT, waitIRq, self._BUFFER12)
        return status

    def pcd_stop_crypto1(self):
        # Clear MFCrypto1On bit
        self.pcd_clear_register_bitmask(
            STATUS2_REG, 0x08
        )  # Status2Reg[7..0] bits are: TempSensClear I2CForceHS reserved reserved MFCrypto1On ModemState[2:0]

    # https://www.nxp.com/docs/en/data-sheet/MF1S70YYX_V1.pdf 12.2
    def mifare_read(self, blockAddr, buffer):
        # Sanity check
        if not buffer or len(buffer) < 16:
            return self.STATUS_NO_ROOM

        # Build command buffer
        buffer[0] = PICC_CMD_MF_READ
        buffer[1] = blockAddr
        crc_buffer = memoryview(buffer)[2:4]
        # Calculate CRC_A
        result = self.pcd_calculate_crc(buffer[0:2], crc_buffer)
        if result != self.STATUS_OK:
            # print("pcd_calculate_crc() error")
            return result

        # Transmit the buffer and receive the response, validate CRC_A.
        status, buffer1, _ = self.pcd_transceive_data(buffer[0:4], checkCRC=True)
        if buffer1:
            buffer[0 : len(buffer1)] = buffer1[0:16]

        return status

    def mifare_write(self, blockAddr, buffer):
        # Sanity check
        if not buffer or len(buffer) < 16:
            return self.STATUS_INVALID

        # Mifare Classic protocol requires two communications to perform a write.
        # Step 1: Tell the PICC we want to write to block blockAddr.
        self._BUFFER2[0] = PICC_CMD_MF_WRITE
        self._BUFFER2[1] = blockAddr
        result = self.pcd_mifare_transceive(self._BUFFER2)
        # print("pcd_mifare_transceive() result:", result)
        # Adds CRC_A and checks that the response is MF_ACK.
        if result != self.STATUS_OK:
            return result

        # Step 2: Transfer the data
        result = self.pcd_mifare_transceive(buffer)
        # print("pcd_mifare_transceive() result:", result)
        # Adds CRC_A and checks that the response is MF_ACK.
        return result

    def mifare_ultralight_write(self, page, buffer):
        # Sanity check
        if not buffer or len(buffer) < 4:
            return self.STATUS_INVALID

        # Build commmand buffer
        cmdBuffer = bytearray(6)
        cmdBuffer[0] = PICC_CMD_UL_WRITE
        cmdBuffer[1] = page
        cmdBuffer[2:6] = buffer

        # Perform the write
        result = self.pcd_mifare_transceive(cmdBuffer)
        # Adds CRC_A and checks that the response is MF_ACK.
        return result

    def mifare_decrement(self, blockAddr, delta):
        return self.mifare_two_step_helper(PICC_CMD_MF_DECREMENT, blockAddr, delta)

    def mifare_increment(self, blockAddr, delta):
        return self.mifare_two_step_helper(PICC_CMD_MF_INCREMENT, blockAddr, delta)

    def mifare_restore(self, blockAddr):
        return self.mifare_two_step_helper(PICC_CMD_MF_RESTORE, blockAddr, 0)

    def mifare_two_step_helper(self, command, blockAddr, data):
        # Step 1: Tell the PICC the command and block address
        self._BUFFER2[0] = command
        self._BUFFER2[1] = blockAddr
        result = self.pcd_mifare_transceive(self._BUFFER2)
        # Adds CRC_A and checks that the response is MF_ACK.
        if result != self.STATUS_OK:
            return result

        # Step 2: Transfer the data
        result = self.pcd_mifare_transceive(data, acceptTimeout=True)
        # Adds CRC_A and accept timeout as success.
        return result

    def mifare_transfer(self, blockAddr):
        # Tell the PICC we want to transfer the result into block blockAddr.
        self._BUFFER2[0] = self.PICC_CMD_MF_TRANSFER
        self._BUFFER2[1] = blockAddr
        return self.pcd_mifare_transceive(
            self._BUFFER2
        )  # Adds CRC_A and checks that the response is MF_ACK.

    def mifare_get_value(self, blockAddr):
        value = 0
        # Read the block
        status = self.mifare_read(blockAddr, self._BUFFER18)
        if status == self.STATUS_OK:
            # Extract the value
            value = (
                (self._BUFFER18[3] << 24)
                | (self._BUFFER18[2] << 16)
                | (self._BUFFER18[1] << 8)
                | (self._BUFFER18[0])
            )
        return status, value

    def mifare_set_value(self, blockAddr, value):
        # Translate the long into 4 bytes; repeated 2x in value block
        self._BUFFER18[0] = self._BUFFER18[8] = value & 0xFF
        self._BUFFER18[1] = self._BUFFER18[9] = (value & 0xFF00) >> 8
        self._BUFFER18[2] = self._BUFFER18[10] = (value & 0xFF0000) >> 16
        self._BUFFER18[3] = self._BUFFER18[11] = (value & 0xFF000000) >> 24
        # Inverse 4 bytes also found in value block
        self._BUFFER18[4] = ~self._BUFFER18[0]
        self._BUFFER18[5] = ~self._BUFFER18[1]
        self._BUFFER18[6] = ~self._BUFFER18[2]
        self._BUFFER18[7] = ~self._BUFFER18[3]
        # Address 2x with inverse address 2x
        self._BUFFER18[12] = self._BUFFER18[14] = blockAddr
        self._BUFFER18[13] = self._BUFFER18[15] = ~blockAddr

        # Write the whole data block
        return self.mifare_write(blockAddr, self._BUFFER18[0:16])

    """Support functions"""

    def pcd_mifare_transceive(self, sendData, acceptTimeout=False):
        result = 0

        # Sanity check
        if not sendData or len(sendData) > 16:
            return self.STATUS_INVALID

        # Copy sendData[] to cmdBuffer[] and add CRC_A
        result = self.pcd_calculate_crc(sendData, self._CRC_BUFFER)
        if result != self.STATUS_OK:
            return result

        cmdBuffer = sendData + self._CRC_BUFFER

        # Transceive the data, store the reply in cmdBuffer[]
        status, rspBuffer, validBits = self.pcd_communicate_with_picc(
            PCD_TRANSCEIVE, 0x30, cmdBuffer, validBits=0
        )
        # print("pcd_communicate_with_picc() status:", status)
        if acceptTimeout and status == self.STATUS_TIMEOUT:
            return self.STATUS_OK

        if status != self.STATUS_OK:
            return status

        # The PICC must reply with a 4 bit ACK
        if len(rspBuffer) != 1 or validBits != 4:
            return self.STATUS_ERROR

        if rspBuffer[0] != 0x0A:
            return self.STATUS_MIFARE_NACK

        return self.STATUS_OK

    def get_status_code_name(self, code):
        name = {
            self.STATUS_OK: "Success.",
            self.STATUS_ERROR: "Error in communication.",
            self.STATUS_COLLISION: "Collission detected.",
            self.STATUS_TIMEOUT: "Timeout in communication.",
            self.STATUS_NO_ROOM: "A buffer is not big enough.",
            self.STATUS_INTERNAL_ERROR: "Internal error in the code. Should not happen.",
            self.STATUS_INVALID: "Invalid argument.",
            self.STATUS_CRC_WRONG: "The CRC_A does not match.",
            self.STATUS_MIFARE_NACK: "A MIFARE PICC responded with NAK.",
        }.get(code, "Unknown error")
        return name

    def picc_get_type(self, sak):
        """
        Translates the SAK (Select Acknowledge) to a PICC type.
        """
        if sak & 0x04:
            # UID not complete
            return self.PICC_TYPE_NOT_COMPLETE

        type = {
            0x09: self.PICC_TYPE_MIFARE_MINI,
            0x08: self.PICC_TYPE_MIFARE_1K,
            0x18: self.PICC_TYPE_MIFARE_4K,
            0x00: self.PICC_TYPE_MIFARE_UL,
            0x10: self.PICC_TYPE_MIFARE_PLUS,
            0x11: self.PICC_TYPE_MIFARE_PLUS,
            0x01: self.PICC_TYPE_TNP3XXX,
        }.get(sak, None)
        if type:
            return type

        if sak & 0x20:
            return self.PICC_TYPE_ISO_14443_4

        if sak & 0x40:
            return self.PICC_TYPE_ISO_18092

        return self.PICC_TYPE_UNKNOWN

    def picc_get_type_name(self, piccType):
        return {
            self.PICC_TYPE_ISO_14443_4: "PICC compliant with ISO/IEC 14443-4",
            self.PICC_TYPE_ISO_18092: "PICC compliant with ISO/IEC 18092 (NFC)",
            self.PICC_TYPE_MIFARE_MINI: "MIFARE Mini, 320 bytes",
            self.PICC_TYPE_MIFARE_1K: "MIFARE 1KB",
            self.PICC_TYPE_MIFARE_4K: "MIFARE 4KB",
            self.PICC_TYPE_MIFARE_UL: "MIFARE Ultralight or Ultralight C",
            self.PICC_TYPE_MIFARE_PLUS: "MIFARE Plus",
            self.PICC_TYPE_TNP3XXX: "MIFARE TNP3XXX",
            self.PICC_TYPE_NOT_COMPLETE: "SAK indicates UID is not complete.",
        }.get(piccType, "Unknown type")

    def picc_dump_to_serial(self, uid: UID):
        key = bytearray(6)  # Create a byte array with length 6

        # UID
        print("Card UID:", uid)

        # PICC type
        piccType = self.picc_get_type(uid.sak)
        print("PICC type:", end=" ")
        print(self.picc_get_type_name(piccType))

        # Dump contents
        if (
            piccType == self.PICC_TYPE_MIFARE_MINI
            or piccType == self.PICC_TYPE_MIFARE_1K
            or piccType == self.PICC_TYPE_MIFARE_4K
        ):
            # All keys are set to FFFFFFFFFFFFh at chip delivery from the factory.
            for i in range(6):
                key[i] = 0xFF
            self.picc_dump_mifare_classic_to_serial(uid, piccType, key)
        elif piccType == self.PICC_TYPE_MIFARE_UL:
            self.picc_dump_mifare_ultralight_to_serial()
        elif (
            piccType == self.PICC_TYPE_ISO_14443_4
            or piccType == self.PICC_TYPE_ISO_18092
            or piccType == self.PICC_TYPE_MIFARE_PLUS
            or piccType == self.PICC_TYPE_TNP3XXX
        ):
            print("Dumping memory contents not implemented for that PICC type.")
        else:
            pass  # No memory dump here

        print()
        self.picc_halt_a()  # Already done if it was a MIFARE Classic PICC.

    def picc_dump_mifare_classic_to_serial(self, uid, piccType, key):
        no_of_sectors = {
            self.PICC_TYPE_MIFARE_MINI: 5,
            self.PICC_TYPE_MIFARE_1K: 16,
            self.PICC_TYPE_MIFARE_4K: 40,
        }.get(piccType, 0)

        # Dump sectors, highest address first.
        if no_of_sectors:
            print("Sector Block   0  1  2  3   4  5  6  7   8  9 10 11  12 13 14 15  AccessBits")
            for i in range(no_of_sectors - 1, -1, -1):
                self.picc_dump_mifare_classic_sector_to_serial(uid, key, i)

        self.picc_halt_a()  # Halt the PICC before stopping the encrypted session.
        self.pcd_stop_crypto1()

    def picc_dump_mifare_classic_sector_to_serial(self, uid, key, sector):
        status = 0
        firstBlock = 0
        no_of_blocks = 0
        isSectorTrailer = False

        if sector < 32:
            no_of_blocks = 4
            firstBlock = sector * no_of_blocks
        elif sector < 40:
            no_of_blocks = 16
            firstBlock = 128 + (sector - 32) * no_of_blocks
        else:
            return

        buffer = bytearray(18)
        blockAddr = 0
        isSectorTrailer = True
        blockOffset = no_of_blocks - 1
        while blockOffset >= 0:
            blockAddr = firstBlock + blockOffset

            if isSectorTrailer:
                if sector < 10:
                    print("   ", end="")
                else:
                    print("  ", end="")
                print(sector, end="   ")
            else:
                print("       ", end="")

            if blockAddr < 10:
                print("   ", end="")
            elif blockAddr < 100:
                print("  ", end="")
            else:
                print(" ", end="")
            print(blockAddr, end="  ")

            if isSectorTrailer:
                status = self.pcd_authenticate(PICC_CMD_MF_AUTH_KEY_A, firstBlock, key, uid)
                if status != self.STATUS_OK:
                    print("pcd_authenticate() failed: ", end="")
                    print(self.get_status_code_name(status))
                    return

            status = self.mifare_read(blockAddr, buffer)
            if status != self.STATUS_OK:
                print("mifare_read() failed: ", end="")
                print(self.get_status_code_name(status))
                continue

            for index in range(16):
                if buffer[index] < 0x10:
                    print(" 0", end="")
                else:
                    print(" ", end="")
                print(hex(buffer[index])[2:].upper(), end="")
                if (index + 1) % 4 == 0:
                    print(" ", end="")

            if isSectorTrailer:
                c1 = buffer[7] >> 4
                c2 = buffer[8] & 0xF
                c3 = buffer[8] >> 4
                c1_ = buffer[6] & 0xF
                c2_ = buffer[6] >> 4
                c3_ = buffer[7] & 0xF
                invertedError = (
                    (c1 != (~c1_ & 0xF)) or (c2 != (~c2_ & 0xF)) or (c3 != (~c3_ & 0xF))
                )
                g = [
                    ((c1 & 1) << 2) | ((c2 & 1) << 1) | ((c3 & 1) << 0),
                    ((c1 & 2) << 1) | ((c2 & 2) << 0) | ((c3 & 2) >> 1),
                    ((c1 & 4) << 0) | ((c2 & 4) >> 1) | ((c3 & 4) >> 2),
                    ((c1 & 8) >> 1) | ((c2 & 8) >> 2) | ((c3 & 8) >> 3),
                ]
                isSectorTrailer = False

            if no_of_blocks == 4:
                group = blockOffset
                firstInGroup = True
            else:
                group = blockOffset // 5
                firstInGroup = (group == 3) or (group != (blockOffset + 1) // 5)

            if firstInGroup:
                print(" [ ", end="")
                print((g[group] >> 2) & 1, end=" ")
                print((g[group] >> 1) & 1, end=" ")
                print((g[group] >> 0) & 1, end=" ")
                print("]", end=" ")
                if invertedError:
                    print(" Inverted access bits did not match! ", end="")

            if group != 3 and (g[group] == 1 or g[group] == 6):
                value = (buffer[3] << 24) | (buffer[2] << 16) | (buffer[1] << 8) | buffer[0]
                print(" Value=0x", end="")
                print(hex(value)[2:].upper(), end="")
                print(" Adr=0x", end="")
                print(hex(buffer[12])[2:].upper(), end="")

            print()
            blockOffset -= 1

        return

    def picc_dump_mifare_ultralight_to_serial(self):
        buffer = bytearray(18)
        print("Page  0  1  2  3")
        # Try the mpages of the original Ultralight. Ultralight C has more pages.
        for page in range(0, 16, 4):
            # Read pages
            status = self.mifare_read(page, buffer)
            if status != self.STATUS_OK:
                print("MIFARE_Read() failed: ", self.get_status_code_name(status))
            # Dump data
            for offset in range(4):
                i = page + offset
                if i < 10:
                    print("  ", end="")
                else:
                    print(" ", end="")
                print(i, end="")
                print("  ", end="")
                for index in range(4):
                    i = 4 * offset + index
                    if buffer[i] < 0x10:
                        print(" 0", end="")
                    else:
                        print(" ", end="")
                    print(hex(buffer[i]), end="")
                print("")

    def mifare_set_access_bits(self, accessBitBuffer, g0, g1, g2, g3):
        c1 = ((g3 & 4) << 1) | ((g2 & 4) << 0) | ((g1 & 4) >> 1) | ((g0 & 4) >> 2)
        c2 = ((g3 & 2) << 2) | ((g2 & 2) << 1) | ((g1 & 2) << 0) | ((g0 & 2) >> 1)
        c3 = ((g3 & 1) << 3) | ((g2 & 1) << 2) | ((g1 & 1) << 1) | ((g0 & 1) << 0)

        accessBitBuffer[0] = (~c2 & 0xF) << 4 | (~c1 & 0xF)
        accessBitBuffer[1] = c1 << 4 | (~c3 & 0xF)
        accessBitBuffer[2] = c3 << 4 | c2

    def mifare_open_uid_backdoor(self, logErrors=False) -> bool:
        self.picc_halt_a()

        response = memoryview(bytearray(32))
        validBits = 7
        status, response1, validBits = self.pcd_transceive_data(
            bytearray([0x40]), validBits=validBits
        )
        if response1:
            response[: len(response1)] = response1
        if status != self.STATUS_OK:
            logErrors and print(
                "Card did not respond to 0x40 after HALT command. Are you sure it is a UID changeable one?"
            )
            logErrors and print("Error name: ", self.get_status_code_name(status))
            return False

        if len(response) != 1 or response[0] != 0x0A:
            logErrors and print(
                "Got bad response on backdoor 0x40 command: ", hex(response[0]), end=""
            )
            logErrors and print(" ( %d valid bits)" % validBits)
            return False

        validBits = 8
        status, response1, validBits = self.pcd_transceive_data(
            bytearray([0x43]), validBits=validBits, rxAlign=0, checkCRC=False
        )
        if response1:
            response[: len(response1)] = response1
        if status != self.STATUS_OK:
            logErrors and print(
                "Error in communication at command 0x43, after successfully executing 0x40"
            )
            logErrors and print("Error name: ", self.get_status_code_name(status))
            return False

        if len(response) != 1 or response[0] != 0x0A:
            logErrors and print(
                "Got bad response on backdoor 0x43 command: ", hex(response[0]), end=""
            )
            logErrors and print(" ( %d valid bits)" % validBits)
            return False

        return True

    def mifare_set_uid(self, newUid, logErrors=False) -> bool:
        if not newUid or len(newUid) == 0 or len(newUid) > 15:
            logErrors and print("New UID buffer empty, size 0, or size > 15 given")
            return False

        key = b"\xff\xff\xff\xff\xff\xff"
        status = self.pcd_authenticate(PICC_CMD_MF_AUTH_KEY_A, 1, key, self._uid)
        if status != self.STATUS_OK:
            if status == self.STATUS_TIMEOUT:
                if self.picc_is_new_card_present() or self.picc_read_card_serial():
                    print(
                        "No card was previously selected, and none are available. Failed to set UID."
                    )
                    return False

                status = self.pcd_authenticate(PICC_CMD_MF_AUTH_KEY_A, 1, key, self._uid)
                if status != self.STATUS_OK:
                    #  We tried, time to give up
                    logErrors and print(
                        "Failed to authenticate to card for reading, could not set UID: ",
                        self.get_status_code_name(status),
                    )
                    return False
            else:
                logErrors and print(
                    "PCD_Authenticate() failed:", self.get_status_code_name(status)
                )

        # Read block 0
        block0_buffer = bytearray(18)
        status = self.mifare_read(0, block0_buffer)
        if status != self.STATUS_OK:
            logErrors and print("MIFARE_Read() failed: ", self.get_status_code_name(status))
            logErrors and print("Are you sure your KEY A for sector 0 is 0xFFFFFFFFFFFF?")
            return False

        # Write new UID to the data we just read, and calculate BCC uint8_t
        bcc = 0
        for i in range(len(newUid)):
            block0_buffer[i] = newUid[i]
            bcc = newUid[i]

        # Write BCC uint8_t to buffer
        block0_buffer[len(newUid)] = bcc

        # Stop encrypted traffic so we can send raw bytes
        self.pcd_stop_crypto1()

        # Activate UID backdoor
        if not self.mifare_open_uid_backdoor(logErrors=logErrors):
            logErrors and print("Activating the UID backdoor failed.")
            return False

        # Write modified block 0 back to card
        status = self.mifare_write(0, memoryview(block0_buffer)[0:16])
        if status != self.STATUS_OK:
            logErrors and print("MIFARE_Write() failed: ", self.get_status_code_name(status))
            return False

        atqa_answer = bytearray(2)
        self.picc_wakeup_a(atqa_answer)
        return True

    def mifare_unbrick_uid_sector(self, logErrors=False) -> bool:
        self.mifare_open_uid_backdoor(logErrors)

        block0_buffer = b"\x01\x02\x03\x04\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

        # Write modified block 0 back to card
        status = self.mifare_write(0, block0_buffer)
        if status != self.STATUS_OK:
            logErrors and print("mifare_write() failed: ", self.get_status_code_name(status))
            return False
        return True

    """Convenience functions - does not add extra functionality"""

    def picc_is_new_card_present(self) -> bool:
        bufferATQA = bytearray(2)
        result = self.picc_request_a(bufferATQA)
        return result == self.STATUS_OK or result == self.STATUS_COLLISION

    def picc_read_card_serial(self) -> bool:
        status = self.picc_select(self._uid)
        return status == self.STATUS_OK

    def pcd_calculate_crc(self, data, result):
        # Stop any active command.
        self.pcd_write_register(COMMAND_REG, PCD_IDLE)
        # Clear the CRCIRq interrupt request bit
        self.pcd_write_register(DIVIRQ_REG, 0x04)
        # FlushBuffer = 1, FIFO initialization
        self.pcd_set_register_bitmask(FIFOLEVEL_REG, 0x80)
        # Write data to the FIFO
        self.pcd_write_bytes(FIFODATA_REG, data)
        # Start the calculation
        self.pcd_write_register(COMMAND_REG, PCD_CALCCRC)

        # Wait for the CRC calculation to complete.
        last_ticks_us = time.ticks_us()
        while True:
            # DivIrqReg[7..0] bits are: Set2 reserved reserved MfinActIRq
            # reserved CRCIRq reserved reserved
            n = self.pcd_read_register(DIVIRQ_REG)
            if n & 0x04:
                # CRCIRq bit set - calculation done
                break

            if time.ticks_us() - last_ticks_us > 89000:
                # The emergency break. We will eventually terminate on this one
                # after 89ms. Communication with the MFRC522 might be down.
                return self.STATUS_TIMEOUT

        self.pcd_write_register(COMMAND_REG, PCD_IDLE)
        # Stop calculating CRC for new content in the FIFO.

        # Transfer the result from the registers to the result buffer
        result[0] = self.pcd_read_register(CRCRESULT_REGL)
        result[1] = self.pcd_read_register(CRCRESULT_REGH)
        return self.STATUS_OK

    def pcd_write_bytes(self, reg, data):
        # print("Write: Reg 0x{:02X}, Value: {}".format(reg, data.hex("-")))
        self._i2c.writeto_mem(self._addr, reg, data)

    def pcd_read_bytes(self, reg, data, rxAlign):
        self._i2c.writeto(self._addr, bytes([reg]))
        self._i2c.readfrom_into(self._addr, data)
        if rxAlign:
            # Create bit mask for bit positions rxAlign..7
            mask = 0
            for j in range(rxAlign, 8):
                mask |= 1 << j
            # Apply mask to both current value of values[0] and the new data in
            # value.
            data[0] = (data[0] & ~mask) | (data[0] & mask)
        # print("Read: Reg 0x{:02X}, Value: {}".format(reg, data.hex("-")))
