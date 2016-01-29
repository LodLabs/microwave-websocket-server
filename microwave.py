from pyA20.gpio import gpio
from pyA20.gpio import port
from pyA20.gpio import connector

from time import sleep
from datetime import datetime, timedelta
import logging

from multiprocessing import Process, Pipe

gpio.init()


def soft_pwm(conn):
    freq = 222 # Hz, mimic Panasonic output
    duty = 0.5 # Start by doing everything

    pwm_port = port.PI19
    gpio.setcfg(pwm_port, gpio.OUTPUT)

    period = 1.0/freq

    period_high = period*duty
    period_low = period*(1-duty)

    while True:
        if conn.poll():
            duty = conn.recv()
            period_high = period*duty
            period_low = period*(1-duty)

        if duty:
            gpio.output(pwm_port, gpio.LOW)
            sleep(period_low)
            gpio.output(pwm_port, gpio.HIGH)
            sleep(period_high)
        else:
            # No pulsing, wait a while and recheck
            gpio.output(pwm_port, gpio.LOW)
            sleep(period)

pwm_conn, pwm_child_conn = Pipe()
pwm_process = Process(target=soft_pwm, args=(pwm_child_conn,))
pwm_process.start()


class Microwave(object):
    def __init__(self):
        logger = logging.getLogger("Microwave")
        logger.info("Initialising microwave")

        # GPIO 0 is port PI19, wired to PWM
        pwm_port = port.PI19 # NOTE: Also set in soft_pwm()
        gpio.setcfg(pwm_port, gpio.OUTPUT)

        # GPIO5 is port PH21, wired to magentron power on/off relay
        relay_port = port.PH21
        gpio.setcfg(relay_port, gpio.OUTPUT)

        # TODO: PI11 clashes with SPI0 which is connected in the DTS
        # Header 23 is port PI11, wired to extra stuff relay - light & mixer
        extra_port = port.PI11
        gpio.setcfg(extra_port, gpio.OUTPUT)

        # TODO: Door sensor

        self._pwm_port = pwm_port
        self._relay_port = relay_port
        self._extra_port = extra_port

        self._time = 0
        self._temperature = 0
        self._target_temperature = 80
        self._power = 100
        self._state = "stopped"

        self._stop_time = datetime.now()

        self.logger = logger

    @property
    def time(self):
        return self._time
    @time.setter
    def time(self, value):
        value = float(value)
        if value < 0 or value > 3600:
            raise ValueError("Time must be positive and no greater than one hour")
        self.logger.info("Time set to {}".format(value))

        # If we are running we need to play some games...
        # When we start running we set the stop time, based on self._time
        # Now we are changing _time we need to update the stop time
        if self._state == "time":
            time_adjust = value - self._time
            self._stop_time += timedelta(seconds=time_adjust)
            self.tick() # Checks if current state is good

        self._time = value

    @property
    def time_remaining(self):
        # Only valid if we are counting down time
        if self._state == "time":
            delta = self._stop_time - datetime.now()
            return delta.seconds
        else:
            return None
    # No setter for time_remaining

    @property
    def target_temperature(self):
        return self._target_temperature
    @target_temperature.setter
    def target_temperature(self, value):
        value = float(value)
        if value < 20 or value > 150:
            raise ValueError("Target temperature must be between 20 and 150 degrees C")
        self.logger.info("Target temperature set to {}".format(value))
        self._target_temperature = value

    @property
    def temperature(self):
        return self._temperature
    @temperature.setter
    def temperature(self, value):
        value = float(value)
        self.logger.debug("Temperature set to {}".format(value))
        self._temperature = value

        # Test to see if we are trying to hit a target, and if we have reached it
        if (self._state == "temperature") and (self._temperature >= self._target_temperature):
            self.state = "stopped"

    @property
    def power(self):
        return self._power
    @power.setter
    def power(self, value):
        # TODO: Low power requires PWM and power pulsing
        value = float(value)
        if value < 0 or value > 100:
            raise ValueError("Power must be a percentage value between 0 and 100")
        self.logger.info("Power set to {}".format(value))
        self._power = value
        # 100% = 50% duty cycle
        pwm_conn.send(value / 200)

    @property
    def state(self):
        return self._state
    @state.setter
    def state(self, value):
        valid_states = ["stopped", "time", "temperature"]
        if value not in valid_states:
            raise ValueError("Invalid state")
        self.logger.info("State set to {}".format(value))

        self._state = value
        getattr(self, "_state_"+value)()

    def _state_stopped(self):
        gpio.output(self._relay_port, gpio.LOW)
        #pwm_conn.send(0)
        # TODO: Keep the light on for a few seconds
        gpio.output(self._extra_port, gpio.LOW)

    def _state_time(self):
        self._stop_time = datetime.now() + timedelta(seconds=self._time)
        self._start()

    def _state_temperature(self):
        self._start()

    def _start(self):
        gpio.output(self._extra_port, gpio.HIGH)
        # Power is set elsewhere, that triggers the PWM
        gpio.output(self._relay_port, gpio.HIGH)



    def tick(self):
        """ Call once a second to update state
        To avoid having another process or thread weirdness the
        microwave object has a tick event that should be called roughly
        once per second. This updates the object state, stopping the
        microwave if required."""
        if self._state == "time" and datetime.now() >= self._stop_time:
            self.state = "stopped"
        # Other states do nothing

