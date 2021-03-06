# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import sys
import json

# WARNING: importing socketio will sometimes cause errors in normal execution
# try to import common instead of common.debugger_communication_cleint
import socketio

import copy
import pathlib

from . import constants as CONSTANTS
from . import utils
import threading
import os
import python_constants as TOPLEVEL_CONSTANTS

from adafruit_circuitplayground.express import cpx
from adafruit_circuitplayground.constants import CPX

# add ref for micropython and clue
abs_path_to_parent_dir = os.path.dirname(
    os.path.join(pathlib.Path(__file__).parent, "..", "..")
)
sys.path.insert(
    0, os.path.join(abs_path_to_parent_dir, TOPLEVEL_CONSTANTS.MICROPYTHON_LIBRARY_NAME)
)

sys.path.insert(0, os.path.join(abs_path_to_parent_dir, TOPLEVEL_CONSTANTS.CLUE_DIR))

from microbit.__model.microbit_model import __mb as mb
from microbit.__model.constants import MICROBIT

from base_circuitpython.base_cp_constants import CLUE
from adafruit_clue import clue

device_dict = {CPX: cpx, MICROBIT: mb, CLUE: clue}
processing_state_event = threading.Event()
previous_state = {}

# similar to utils.send_to_simulator, but for debugging
# (needs handle to device-specific debugger)
def debug_send_to_simulator(state, active_device):
    global previous_state
    if state != previous_state:
        previous_state = copy.deepcopy(state)

        updated_state = utils.update_state_with_device_name(state, active_device)
        message = utils.create_message(updated_state)

        update_state(json.dumps(message))


# Create Socket Client
sio = socketio.Client(reconnection_attempts=CONSTANTS.CONNECTION_ATTEMPTS)

# TODO: Get port from process_user_code.py via childprocess communication


# Initialize connection
def init_connection(port=CONSTANTS.DEFAULT_PORT):
    sio.connect("http://localhost:{}".format(port))


# Transfer the user's inputs to the API
def __update_api_state(data):
    try:
        event_state = json.loads(data)
        active_device_string = event_state.get(CONSTANTS.ACTIVE_DEVICE_FIELD)

        if active_device_string is not None:
            active_device = device_dict.get(active_device_string)
            if active_device is not None:
                active_device.update_state(event_state.get(CONSTANTS.STATE_FIELD))

    except Exception as e:
        print(CONSTANTS.ERROR_SENDING_EVENT, e, file=sys.stderr, flush=True)


# Method : Update State
def update_state(state):
    processing_state_event.clear()
    sio.emit("updateState", state)
    processing_state_event.wait()


# Event : Button pressed (A, B, A+B, Switch)
# or Sensor changed (Temperature, light, Motion)
@sio.on("input_changed")
def input_changed(data):
    sio.emit("receivedState", data)
    __update_api_state(data)


@sio.on("received_state")
def received_state(data):
    processing_state_event.set()


@sio.on("process_disconnect")
def process_disconnect(data):
    sio.disconnect()
