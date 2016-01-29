from pyBusPirateLite.I2Chigh import I2Chigh, I2CPins, I2CSpeed

import logging

# TODO: USB Bus drops out when power to the microwave is turned off
#       This causes ttyUSB0 to go away, for a while
#       When it comes back, it could be ttyUSB0 - map to /dev/buspirate
#       Need to recover from this...
#
# Fails in self.get_bulk(self.i2c_addr, 0x80, 64*2)
# SerialException: write failed: [Errno 5] Input/output error
# Can we call init from inside the object?

class GridEye(object):
    def __init__(self, device="/dev/buspirate"):
        logger = logging.getLogger("GridEye")
        logger.info("Initialising BusPirate")

        i2c = I2Chigh(device, 115200)

        if i2c.BBmode():
            logger.debug("BBMode ok")
        else:
            logger.error("BBMode failed")
            raise Exception("Buspirate failed to initialise BBMode")

        if i2c.enter_I2C():
            logger.debug("I2C mode ok")
        else:
            logger.error("I2C mode failed")
            raise Exception("Buspirate failed to initialise I2C Mode")

        if i2c.cfg_pins(I2CPins.POWER | I2CPins.PULLUPS):
            logger.debug("I2C pin config ok")
        else:
            logger.error("I2C pin config failed")
            raise Exception("Buspirate failed to configure I2C pins")

        if i2c.set_speed(I2CSpeed._100KHZ):
            logger.debug("I2C speed set ok")
        else:
            logger.error("I2C speed set failed")
            raise Exception("Buspirate failed to configure I2C speed")

        i2c.timeout(0.2)

        self.i2c = i2c
        self.i2c_addr = 0xD0 >> 1
        self.logger = logger

    def get_run_mode(self):
        run_mode = self.i2c.get_byte(self.i2c_addr, 0x00)
        self.logger.debug("Run mode: 0x{:02X}".format(run_mode))
        return run_mode

    def get_status(self):
        ge_stat = self.i2c.get_byte(self.i2c_addr, 0x04)
        self.logger.debug("Status: 0x{:02X}".format(ge_stat))
        if ge_stat & 0b1000: self.logger.info("\tThermistor output overflow")
        if ge_stat &  0b100: self.logger.info("\tTemperature output overflow")
        if ge_stat &   0b10: self.logger.info("\tInterrupt triggered")
        return ge_stat

    def get_thermistor(self):
        ge_therm = self.i2c.get_word(self.i2c_addr, 0x0E)
        # Need to reverse the byte order... :(
        ge_therm = (ge_therm % 256) * 256 + math.floor(ge_therm / 256)
        ge_therm_C = ge_therm * 0.0625
        self.logger.debug("Thermistor {} == {} degC".format(ge_therm, ge_therm_C))
        return ge_therm_C

    def get_bulk(grideye, i2caddr, addr, num_bytes):
        """ Get a large chunk of data from device """
        self = grideye.i2c # Psuedo I2C device function
        self.send_start_bit()
        stat = self.bulk_trans(2, [i2caddr << 1, addr])
        self.send_start_bit()
        stat += self.bulk_trans(1, [i2caddr << 1 | 1])
        ret = []
        for i in range(num_bytes-1):
            ret.append(self.read_byte())
            self.send_ack()
        ret.append(self.read_byte())
        self.send_nack()
        self.send_stop_bit()
        return ret

    def get_pixels(self):
        raw_pixel_data = self.get_bulk(self.i2c_addr, 0x80, 64*2)
        raw_pixels = [ord(b)*256 + ord(a) for a,b in zip(raw_pixel_data,raw_pixel_data[1:])[::2]]
        temp_pixels_C = [p * 0.25 for p in raw_pixels]

        # Roughly a 8x8 grid
        pixel_grid = zip(*[iter(temp_pixels_C)]*8)

        for row in pixel_grid:
            self.logger.debug("  ".join("{:0.2f}".format(cell) for cell in row))

        return pixel_grid
