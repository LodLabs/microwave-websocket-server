from tornado.ioloop import IOLoop, PeriodicCallback
import tornado.web
import tornado.websocket
from tornado.escape import json_encode, json_decode

from grideye import GridEye
from microwave import Microwave

#from grideye_stub import GridEye
#from microwave_stub import Microwave

from datetime import datetime

import logging

logging.basicConfig(level=logging.DEBUG)

clients = []
image_clients = []

eye = GridEye()
microwave = Microwave()

web_root = "../gui/"

def get_status():
    return {
        "time" : microwave.time,
        "time_remaining" : microwave.time_remaining,
        "temperature" : microwave.temperature,
        "target_temperature" : microwave.target_temperature,
        "power" : microwave.power,
        "state" : microwave.state,
    }

class IndexHandler(tornado.web.RequestHandler):
  @tornado.web.asynchronous
  def get(request):
    logging.getLogger("IndexHandler").info("FALLBACK")
    with open(web_root + "index.html", 'r') as file:
        request.write(file.read())
    request.finish()

class WebSocketControlHandler(tornado.websocket.WebSocketHandler):
  def open(self, *args):
    logging.getLogger("WebSocketControlHandler").info("open")
    clients.append(self)

  def check_origin(self, origin):
    return True # Allow any origin

  def on_message(self, raw_message):
    logger = logging.getLogger("WebSocketControlHandler")

    logger.debug(raw_message)

    try:
        message = json_decode(raw_message)
    except ValueError:
        logger.warn("Non-JSON message {}".format(raw_message))
        return

    self.process_message(message)

    json_status = json_encode(get_status())

    for client in clients:
        client.write_message(json_status)

  def on_close(self):
    logging.getLogger("WebSocketControlHandler").info("close")
    clients.remove(self)

  def process_message(self, message):
    logger = logging.getLogger("WebSocketControlHandler")

    # Blank messages are valid, extra fields are ignored
    # Each key must have it's own defined parser
    # State must be must be last
    message_keys = ["time", "target_temperature", "power", "state"]
    for key in message_keys:
        if key in message: # TODO: If message is a string - this dies hard
            try:
                setattr(microwave, key, message[key])
            except ValueError:
                logger.warn("Invalid JSON, invalid value for {}: {}".format(key, message))

class WebSocketImageHandler(tornado.websocket.WebSocketHandler):
    def open(self, *args):
        logging.getLogger("WebSocketImageHandler").info("open")
        image_clients.append(self)

    def check_origin(self, origin):
        return True # Allow any origin

    def on_close(self):
        logging.getLogger("WebSocketImageHandler").info("close")
        image_clients.remove(self)

    def on_message(self, message):
        pass # 1-way comms


app = tornado.web.Application([
    (r'/control', WebSocketControlHandler),
    (r'/thermal_image', WebSocketImageHandler),
    # A touch dodgy, anything with a literal . in it is a real file
    # Anything without a dot is probably a fancy angular fake path
    (r'/(.*\..*)', tornado.web.StaticFileHandler, {"path": web_root, "default_filename": "index.html"}),
    ], default_handler_class=IndexHandler
)

app.listen(8042)

def update_grideye():
    pixels = eye.get_pixels()
    flat = [pixel for row in pixels for pixel in row]
    max_t = max(flat)
    min_t = min(flat)

    microwave.temperature = max_t

    json_pixels = json_encode(pixels)

    for client in image_clients:
        client.write_message(json_pixels)

def update_microwave():
    microwave.tick()

    json_status = json_encode(get_status())

    for client in clients:
        client.write_message(json_status)


PeriodicCallback(update_grideye, 1000).start()
PeriodicCallback(update_microwave, 1000).start()

IOLoop.instance().start()
