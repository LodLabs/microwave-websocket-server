from time import sleep
from datetime import datetime, timedelta
import logging

from multiprocessing import Process, Pipe

def soft_pwm(conn):
    freq = 222 # Hz, mimic Panasonic output
    duty = 0 # Start by doing nothing

    period = 1.0/freq
    period_high = period*duty
    period_low = period*(1-duty)

    while True:
        if conn.poll():
            duty = conn.recv()
        sleep(period)

pwm_conn, pwm_child_conn = Pipe()
pwm_process = Process(target=soft_pwm, args=(pwm_child_conn,))
pwm_process.start()


class Microwave(object):
    def __init__(self):
        logger = logging.getLogger("MicrowaveSTUB")
        logger.info("Initialising microwave STUB")

        self._pwm_port = None
        self._relay_port = None
        self._extra_port = None

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
        self._temperature = value

        # Test to see if we are trying to hit a target, and if we have reached it
        if (self._state == "temperature") and (self._temperature >= self._target_temperature):
            self.state = "stopped"

    @property
    def power(self):
        return self._power
    @power.setter
    def power(self, value):
        value = float(value)
        if value < 0 or value > 100:
            raise ValueError("Power must be a percentage value between 0 and 100")
        self.logger.info("Power set to {}".format(value))
        self._power = value

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
        pwm_conn.send(0)

    def _state_time(self):
        self._stop_time = datetime.now() + timedelta(seconds=self._time)
        self._start()

    def _state_temperature(self):
        self._start()

    def _start(self):
        pwm_conn.send(self._power / 100)



    def tick(self):
        """ Call once a second to update state
        To avoid having another process or thread weirdness the
        microwave object has a tick event that should be called roughly
        once per second. This updates the object state, stopping the
        microwave if required."""
        if self._state == "time" and datetime.now() >= self._stop_time:
            self.state = "stopped"
        # Other states do nothing

