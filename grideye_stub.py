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

        self.i2c = None
        self.i2c_addr = 0xD0 >> 1
        self.logger = logger

    def get_run_mode(self):
        run_mode = 0
        self.logger.debug("Run mode: 0x{:02X}".format(run_mode))
        return run_mode

    def get_status(self):
        ge_stat = 0
        self.logger.debug("Status: 0x{:02X}".format(ge_stat))
        if ge_stat & 0b1000: self.logger.info("\tThermistor output overflow")
        if ge_stat &  0b100: self.logger.info("\tTemperature output overflow")
        if ge_stat &   0b10: self.logger.info("\tInterrupt triggered")
        return ge_stat

    def get_thermistor(self):
        return 22

    def get_pixels(self):
        temp_pixels_C = [30+i*j for i in range(8) for j in range(8)]

        # Roughly a 8x8 grid
        pixel_grid = zip(*[iter(temp_pixels_C)]*8)

        return pixel_grid
