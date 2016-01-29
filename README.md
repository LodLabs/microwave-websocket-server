# Microwave Websocket Server

This websocket server was created to demo the microwave at the 2016 LCA.
It uses a nice flexible websocket framework.

This code is not recommended for any use that requires executing it.


# To run

python server.py

# Debug client
wsdump ws://localhost:8042/control
wsdump ws://localhost:8042/thermal_image

# Requirements
python-pybuspiratelite_597-1_all.deb
python-websocket
python-tornado
python-serial


# Sample Messages
{"temperature":33}
{"time":10,"state":"time"}
{"state":"stopped"}
{"target_temperature":30,"state":"temperature"}

