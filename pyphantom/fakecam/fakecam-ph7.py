#!/usr/bin/env python
from __future__ import print_function

import logging
import os
import sys

logger = logging.getLogger(__name__)

import glob
import socket
import time
from threading import Thread
import yaml

from fakecam_data import state, answers

camthread = None


def get(keystring):
    sub = keystring.split(".")
    out = state
    for key in sub:
        out = out[key]
    if type(out) is dict:
        out = "{}: {}".format(key, out)
    return out


def threaded(fn):
    def wrapper(*args, **kwargs):
        t = Thread(target=fn, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()

    return wrapper


@threaded
def send_frame(socket, cine, count=1):
    script_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    raw_path = os.path.join(script_path, "./takes-ph7/{}.raw".format(cine))
    with open(raw_path) as f:
        logger.debug("sending {}.raw".format(cine))
        socket.sendall(f.read() * count)


@threaded
def save(fsave):
    state["fstat"]["in_progress"] = fsave["lastframe"] - fsave["firstframe"]
    while state["fstat"]["in_progress"]:
        state["fstat"]["in_progress"] -= 1
        time.sleep(0.001)


@threaded
def ferase():
    state["fstat"]["in_progress"] = 100

    state["mag"]["state"] = 8
    logger.info("CineMag erasing")

    while state["fstat"]["in_progress"]:
        state["fstat"]["in_progress"] -= 1
        time.sleep(0.1)

    state["mag"]["takes"] = 0

    state["mag"]["state"] = 2
    logger.info("CineMag initialising")

    time.sleep(1)

    state["mag"]["state"] = 3
    logger.info("CineMag scanning")

    time.sleep(1)

    state["mag"]["state"] = 4
    logger.info("CineMag ready")


def responder(clientsocket, address):
    logger.info("connection from {}".format(address))
    while 1:
        command = clientsocket.recv(1024)
        answer = None
        img = ""
        if command:
            logger.debug("got command: {}".format(command))
            try:
                if command == "rec 1\n":
                    state["c1"]["state"] = {"WTR"}

                elif command == "trig\n":
                    state["c1"]["state"] = {"RDY"}

                elif command.startswith("get"):
                    answer = get(command.replace("get ", "").strip())

                elif command.startswith("img"):
                    clean = " ".join(command.lstrip("img ").split()).replace("\\", "")
                    img = yaml.load(clean)
                    answer = "Ok! {{ cine: {cine}, res: {res}, fmt: P10 }}".format(
                        cine=img["cine"], res=state["fc{}".format(img["cine"])]["res"]
                    )

                elif command.startswith("set"):
                    option, value = command.strip().lstrip("set ").split(": ")
                    split = option.split(".")
                    if len(split) == 2:
                        key, subkey = split
                        state[key][subkey] = value
                    elif len(split) == 3:
                        key, subkey, subsubkey = split
                        state[key][subkey][subsubkey] = value
                    answer = "Ok!"

                elif command.startswith("vplay"):
                    clean = " ".join(command.lstrip("vplay ").split()).replace("\\", "")
                    vplay = yaml.load(clean)
                    try:
                        for key, value in vplay.iteritems():
                            state["video"]["play"][key] = value
                    except:
                        logger.warning("vplay: {}".format(vplay))
                    answer = "Ok!"

                elif command.startswith("fsave"):
                    clean = " ".join(command.lstrip("fsave ").split()).replace("\\", "")
                    fsave = yaml.load(clean)
                    save(fsave)
                    answer = "Ok!"

                elif command.startswith("attach"):
                    command = "attach"

                elif command.startswith("startdata"):
                    clean = " ".join(command.lstrip("startdata ").split()).replace("\\", "")
                    startdata = yaml.load(clean)
                    print(startdata)
                    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    data_socket.connect((address[0], startdata["port"]))
                    answer = "Ok!"

                elif command.startswith("ferase"):
                    ferase()
                    answer = "Ok!"

                if answer is None:
                    answer = str(answers[command.strip()])

                logger.debug(repr(answer))

                # uncomment to simulate slow connection
                # import time; time.sleep(0.6)

                clientsocket.send(str(answer) + "\r\n")

                if img:
                    send_frame(data_socket, img["cine"], img["cnt"])

            except KeyError:
                logger.error("command not implemented: {}".format(command))
                clientsocket.send("command not implemented.." + "\r\n")
                raise

        else:
            logger.error("connection lost")
            break


def discover(discoversocket):
    myip = socket.gethostbyname(socket.gethostname())
    while True:
        data = ""
        try:
            data, addr = discoversocket.recvfrom(1024)
        except socket.error:
            pass
        if data == "phantom?":
            logger.info("hello phantom :P")
            # discoversocket.sendto('{} {} 4001 16001 "FAKE_CAMERA"'.format("PH16", '7115'), addr)
            discoversocket.sendto("PH7 7115", addr)


def delete_takes():
    for key in state.keys():
        if key.startswith("fc"):
            del state[key]


def load_takes():
    delete_takes()
    script_path = os.path.dirname(os.path.realpath(sys.argv[0]))

    takes = 0
    for yaml_file in glob.glob("{}/takes-ph7/*.data".format(script_path)):
        take_index = os.path.splitext(os.path.basename(yaml_file))[0]

        if os.path.exists("{}/takes-ph7/{}.raw".format(script_path, take_index)):
            with open(yaml_file) as y:
                clean = " ".join(y.read().split()).replace("\\", "")
                take_info = yaml.load(clean)
                # use first key of take_info because we renumber the takes
                state["fc{}".format(take_index)] = take_info[take_info.keys()[0]]
            logger.info("Take {} loaded".format(take_index))
            takes += 1

    state["mag"]["takes"] = takes


@threaded
def run():
    try:
        discoversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discoversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discoversocket.bind(("", 7380))
        # discoversocket.setblocking(0)

        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(("", 7115))
        serversocket.listen(5)

        d = Thread(target=discover, args=(discoversocket,))
        d.daemon = True
        d.start()

        while True:
            (clientsocket, address) = serversocket.accept()
            t = Thread(target=responder, args=(clientsocket, address))
            t.daemon = True
            t.start()

    except KeyboardInterrupt:
        logger.error("Keyboard Interrupt: stopping server")

    finally:
        discoversocket.close()
        serversocket.close()


load_takes()


if __name__ == "__main__":
    FORMAT = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    logger.debug("Starting FakeCam")

    run()
    while True:
        time.sleep(100)
