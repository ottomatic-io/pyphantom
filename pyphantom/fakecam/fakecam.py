#!/usr/bin/env python3
import glob
import logging
import os
import socket
import sys
import time
from io import StringIO
from threading import Thread

import yaml

from pyphantom.fakecam import ximg_send
from pyphantom.fakecam.fakecam_data import state, answers

logger = logging.getLogger(__name__)
FORMAT = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)

camthread = None

takes_path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "takes")

if not os.path.isdir(takes_path):
    takes_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "takes")


def threaded(fn):
    def wrapper(*args, **kwargs):
        t = Thread(target=fn, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()

    return wrapper


def parse_simple(response):
    clean = response.replace(" ", "").split("{")[1].split("}")[0].split(",")

    out = {}
    for x in clean:
        try:
            key, value = x.split(":")
        except ValueError:
            split = x.split(":")
            key, value = split[0], ":".join(split[1:])
        out[key] = value

    return out


def phantom_format(key, value, stream=None):
    if stream is None:
        stream = StringIO()
    stream.write("{} : ".format(key))
    if isinstance(value, (int, float)):
        stream.write(str(value))
    elif isinstance(value, str):
        stream.write('"{}"'.format(value))
    elif isinstance(value, list):
        stream.write("{")
        for item in value:
            stream.write(" {}".format(item))
        stream.write(" }")
    elif isinstance(value, dict):
        phantom_dictformat(value, stream)

    return stream.getvalue()


def phantom_dictformat(mydict, stream):
    if not isinstance(mydict, dict):
        raise AssertionError()

    stream.write("{ ")
    first = True
    for key, value in mydict.items():
        if not first:
            stream.write(", ")
        phantom_format(key, value, stream)

        first = False
    stream.write(" }")


def get(state, keystring):
    if keystring == "*":
        return phantom_format("*", "NOT IMPLEMENTED")
    sub = keystring.split(".")
    out = state
    for key in sub:
        out = out[key]

    return phantom_format(sub[-1], out)


@threaded
def send_frame(socket, cine, count=1):
    if cine == -1:
        cine = 0
    raw_path = os.path.join(takes_path, "./{}.raw".format(cine))
    with open(raw_path, "rb") as f:
        logger.debug("sending {}.raw".format(cine))
        socket.sendall(f.read() * count)


@threaded
def save(fsave):
    state["mag"]["progress"] = fsave["lastframe"] - fsave["firstframe"]
    while state["mag"]["progress"]:
        state["mag"]["progress"] -= 1
        time.sleep(0.001)


@threaded
def ferase():
    state["mag"]["progress"] = 100

    state["mag"]["state"] = 8
    logger.info("CineMag erasing")

    while state["mag"]["progress"]:
        state["mag"]["progress"] -= 1
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


def responder(clientsocket, address, clientsocket_data, address_data):
    ssrc = 0

    logger.info("connection from {}".format(address))
    while True:
        command = clientsocket.recv(1024).decode("ascii").strip()
        answer = None
        img = ""
        ximg = ""
        if command:
            logger.debug("got command: {}".format(command))
            try:
                if command == "rec 1\n":
                    state["c1"]["state"] = ["WTR"]

                elif command == "trig\n":
                    state["c1"]["state"] = ["RDY"]

                elif command.startswith("get"):
                    keystring = command.replace("get ", "").strip()
                    answer = get(state, keystring)

                elif command.startswith("img"):
                    img = parse_simple(command)
                    answer = "Ok! {{ cine: {cine}, res: {res}, fmt: P10 }}".format(
                        cine=img["cine"], res=state[f"fc{img['cine']}"]["res"]
                    )

                elif command.startswith("ximg"):
                    ximg = parse_simple(command)
                    answer = "Ok! {{ cine: {cine}, res: {res}, fmt: P10, ssrc: {ssrc} }}".format(
                        cine=ximg["cine"], res=state["fc{}".format(ximg["cine"])]["res"], ssrc=ssrc
                    )
                    ximg["ssrc"] = ssrc

                    ssrc += 1

                elif command.startswith("setrtc"):
                    answer = "Ok!"

                elif command.startswith("set"):
                    option, value = command.strip().lstrip("set ").split()
                    try:
                        value = int(value)
                    except ValueError:
                        pass

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
                    vplay = yaml.safe_load(clean)
                    try:
                        for key, value in vplay.items():
                            state["video"]["play"][key] = int(value)
                    except:
                        logger.warning("vplay: {}".format(vplay))
                    answer = "Ok!"

                elif command.startswith("fsave"):
                    clean = " ".join(command.lstrip("fsave ").split()).replace("\\", "")
                    fsave = yaml.safe_load(clean)
                    save(fsave)
                    answer = "Ok!"

                elif command.startswith("attach"):
                    command = "attach"

                elif command.startswith("ferase"):
                    ferase()
                    answer = "Ok!"

                if answer is None:
                    answer = str(answers[command.strip()])

                logger.debug(repr(answer))

                # uncomment to simulate slow connection
                # import time; time.sleep(0.6)

                clientsocket.send(answer.encode("ascii") + b"\r\n")

                if ximg:
                    ximg_send.send_frame(int(ximg["cine"]), int(ximg["cnt"]), ximg["dest"], ximg["ssrc"])
                if img:
                    send_frame(clientsocket_data, int(img["cine"]), int(img["cnt"]))

            except KeyError:
                logger.error("command not implemented: {}".format(command))
                clientsocket.send(b"command not implemented..\r\n")
                raise

        else:
            logger.error("connection lost")
            break


def discover(discoversocket):
    while True:
        try:
            data, addr = discoversocket.recvfrom(1024)
            if data == b"phantom?":
                logger.info("hello phantom :P")
                discoversocket.sendto(b'PH16 7115 4001 16001 "FAKE_CAMERA"', addr)
        except socket.error:
            pass


def delete_takes():
    for key in list(state.keys()):
        if key.startswith("fc"):
            del state[key]


def load_takes():
    delete_takes()

    takes = 0
    for yaml_file in glob.glob("{}/*.data".format(takes_path)):
        take_index = os.path.splitext(os.path.basename(yaml_file))[0]

        if os.path.exists("{}/{}.raw".format(takes_path, take_index)):
            with open(yaml_file) as y:
                clean = " ".join(y.read().split()).replace("\\", "")
                take_info = yaml.safe_load(clean)
                # use first key of take_info because we renumber the takes
                state["fc{}".format(take_index)] = take_info[list(take_info.keys())[0]]
            logger.info("Take {} loaded".format(take_index))
            takes += 1

    state["mag"]["takes"] = takes
    state["fc-1"] = state["fc0"]


@threaded
def run():
    logger.info("Starting FakeCam")

    try:
        discoversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discoversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discoversocket.bind(("", 7380))
        # discoversocket.setblocking(0)

        port = 7115

        while True:
            try:
                serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                serversocket.bind(("", port))
                serversocket.listen(5)

                serversocket_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                serversocket_data.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                serversocket_data.bind(("", port + 1))
                serversocket_data.listen(5)

                break

            except:
                raise

        d = Thread(target=discover, args=(discoversocket,))
        d.daemon = True
        d.start()

        while True:
            (clientsocket, address) = serversocket.accept()
            (clientsocket_data, address_data) = serversocket_data.accept()
            t = Thread(target=responder, args=(clientsocket, address, clientsocket_data, address_data))
            t.daemon = True
            t.start()

    except KeyboardInterrupt:
        logger.error("Keyboard Interrupt: stopping server")

    except:
        raise

    finally:
        try:
            discoversocket.close()
            serversocket.close()
            serversocket_data.close()
        except UnboundLocalError:
            pass


load_takes()

if __name__ == "__main__":
    try:
        if sys.argv[1] in ["--ximg", "-x"]:
            logger.info("Simulating 10GbE connection")
            state["info"]["features"] += " ximg"
    except IndexError:
        pass

    run()
    while True:
        time.sleep(100)
