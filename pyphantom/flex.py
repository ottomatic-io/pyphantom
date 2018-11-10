import errno
import logging
import socket
import time
from multiprocessing import Lock
from threading import current_thread

import yaml
from cached_property import cached_property_with_ttl, cached_property

from pyphantom.structures import PhantomStructures
from pyphantom.utils import threaded
from pyphantom.network import get_mac, get_interface_of_ip, get_mac_of_interface, get_networks

logger = logging.getLogger()


def angle2exp(rate, angle):
    return 1.0 / rate * 1000000000 / (360.0 / angle)


def exp2angle(rate, exp):
    return int(round(360 / (1 / float(rate) * 1000000000 / float(exp))))


class CameraError(Exception):
    pass


class ConnectionError(Exception):
    pass


class FrameOutsideRangeError(Exception):
    pass


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


def parse_flag_list(response):
    return response.split("{")[1].split("}")[0].strip().split()


def parse_response(response):
    # if response.startswith('state'):
    #    return response

    brackets = response.count("{")

    if brackets == 1 and "\t" not in response:
        if response.count(":") > 1:
            return parse_simple(response)
        else:
            return parse_flag_list(response)

    elif brackets:
        clean = " ".join(response.lstrip("Ok!").split()).replace("\\", "")

        # Remove key and replace by X as a marker so it can easily be removed.
        # I am sure there is a cleaner way to do this.
        clean = ":".join(clean.split(":")[1:])
        clean = "X :" + clean

        try:
            return yaml.safe_load(clean)["X"]
        except yaml.parser.ParserError:
            raise

    elif response.startswith("Ok!"):
        return response

    elif response.startswith("ERR: start+count frame outside range"):
        raise FrameOutsideRangeError()

    elif response.startswith("ERR"):
        raise CameraError(response.replace("ERR: ", "").capitalize())

    else:
        try:
            return response.split(" : ")[1].strip().replace('"', "")
        except:
            return response.strip()


class Phantom(object):
    def __init__(self, ip, port=7115, protocol="PH16"):
        self.ip = ip
        self.port = int(port)
        self.protocol = protocol
        self.interface = None
        self.interface_mac = None

        self.connected = False
        self.alive = False

        self.socket = None
        self.socket_data = None

        self.lock = Lock()
        self.connect_lock = Lock()
        self.data_lock = Lock()

        self.last_message = 0

    fake_ssrc_counter = 0

    @property
    def structures(self):
        return PhantomStructures(self)

    def get_fake_ssrc(self):
        with self.lock:
            self.fake_ssrc_counter += 1
            if self.fake_ssrc_counter > 65535:
                self.fake_ssrc_counter = 0
        return self.fake_ssrc_counter

    @cached_property
    def mac(self):
        try:
            return get_mac(self.ip)
        except ValueError:
            logger.warning("Could not get mac address for {}".format(self.ip))
            return "feedfacebeef"

    @cached_property
    def model(self):
        return self.ask("get info.model")

    @cached_property_with_ttl(ttl=1)
    def takes(self):
        return Takes(self)

    @cached_property_with_ttl(ttl=1)
    def ram_takes(self):
        return RamTakes(self)

    @cached_property_with_ttl(ttl=0.03)
    def recstatus(self):
        return "WTR" in self.ask("get c1.state")

    @cached_property_with_ttl(ttl=0.5)
    def c1(self):
        return self.get_takeinfo("c1")

    @cached_property_with_ttl(ttl=0.5)
    def defc(self):
        return self.ask("get defc")

    @cached_property_with_ttl(ttl=0.5)
    def shutter_angle(self):
        return exp2angle(self.defc["rate"], self.defc["exp"])

    @property
    def progress(self):
        try:
            return int(self.ask("get mag.progress"))
        except ValueError:
            return 0

    @property
    def mag_state(self):
        try:
            return int(self.ask("get mag.state"))
        except TypeError:
            return

    @cached_property_with_ttl(ttl=0.5)
    def battv(self):
        return round(float(self.ask("get info.battv")) / 1000, 1)

    @cached_property_with_ttl(ttl=0.5)
    def vcdina(self):
        try:
            return round(float(self.ask("get info.vcdina")), 1)
        except CameraError:
            return 0

    @cached_property_with_ttl(ttl=0.5)
    def vcdinb(self):
        try:
            return round(float(self.ask("get info.vcdinb")), 1)
        except CameraError:
            return 0

    @cached_property_with_ttl(ttl=0.5)
    def battstate(self):
        return int(self.ask("get info.battstate"))

    @property
    def video_play(self):
        return self.ask("get video.play")

    @property
    def resolution(self):
        if int(self.defc["meta"]["crop"]) or int(self.defc["meta"]["resize"]):
            return "{}x{}".format(self.defc["meta"]["ow"], self.defc["meta"]["oh"])
        else:
            return self.defc["res"]

    def connect(self):
        with self.connect_lock:
            if not self.connected:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(4.0)
                self.socket.connect((self.ip, self.port))

                if self.protocol == "PH16":
                    self.socket_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket_data.settimeout(4.0)
                    data_port = self.port + 1
                    self.socket_data.connect((self.ip, data_port))
                    socket_data_port = self.socket_data.getsockname()[1]

                    self.ask("attach {}".format(socket_data_port)).strip()

                elif self.protocol == "PH7":
                    data_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    data_server.bind(("", 0))
                    data_server.listen(5)
                    data_server_port = data_server.getsockname()[1]

                    self.ask("startdata {{port: {}}}".format(data_server_port)).strip()
                    self.socket_data, address = data_server.accept()

                self.connected = True

                # sync camera clock to this systems clock
                self.set_rtc()

                self.interface = get_interface_of_ip(self.ip)
                self.interface_mac = get_mac_of_interface(self.interface)

                logger.info("Connected to a {} at {} on interface {}".format(self.model, self.ip, self.interface))
                if self.protocol == "PH16":
                    cinestation_firmware_version = self.ask("get info.fver")
                    cam_firmware_version = self.ask("get fc0.info.fver")
                elif self.protocol == "PH7":
                    cinestation_firmware_version = self.ask("get info.swver")
                    cam_firmware_version = self.ask("get fc0.info.swver")

                logger.info("Cinestation firmware version: {}".format(cinestation_firmware_version))
                logger.info("Camera firmware version: {}".format(cam_firmware_version))

    @threaded
    def check_alive(self, check_interval=0.4):
        while True:
            if not current_thread().parent_thread.is_alive():
                logger.warning("Parent thread died. Stopping check_alive")
                break

            if self.connected:
                try:
                    _ = self.mag_state
                    time.sleep(check_interval)
                except Exception as e:
                    logger.warning("Connection dead. %s", e)
                    self.disconnect()
            else:
                break

    def disconnect(self):
        self.alive = False
        self.connected = False
        if self.socket:
            self.socket.close()
        if self.socket_data:
            self.socket_data.close()
        logger.info("Disconnected")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def toggle(self):
        if self.alive:
            commands = ["rec 1", "trig"]
            self.ask(commands[self.recstatus])

    def get_takeinfo(self, take, keys=None):
        keys = keys or ["firstfr", "lastfr", "in", "out", "frcount", "state"]
        takeinfo = {}
        for key in keys:
            takeinfo[key] = self.ask("get {}.{}".format(take, key))

        return takeinfo

    def recvall(self, n):
        data = ""
        while len(data) < n:
            packet = self.socket_data.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def recv_frame(self, frame_size, frame_header):
        data = bytearray(frame_size + len(frame_header))
        data[: len(frame_header)] = frame_header
        view = memoryview(data)
        view = view[len(frame_header) :]
        to_read = frame_size
        while to_read:
            nbytes = self.socket_data.recv_into(view, to_read)
            view = view[nbytes:]
            to_read -= nbytes
        return data

    @staticmethod
    def recv_end(the_socket):
        end = "\r\n"
        escaped_crlf = "\\\r\n"

        total_data = []

        while True:
            data = the_socket.recv(8192).decode("ascii")
            if not data:
                logger.warning("No data..")
                break
            total_data.append(data)

            # In case last received packet is only one byte we need to check the last two packets
            last_2_packets = "".join(total_data[-2:])
            if last_2_packets.endswith(end) and not last_2_packets.endswith(escaped_crlf):
                break

        return "".join(total_data)

    def ask(self, command: str):
        try:
            with self.lock:
                # logger.debug('Command: {}'.format(command))
                self.socket.sendall(command.encode("ascii") + b"\n")
                response = self.recv_end(self.socket)

                self.alive = True
                self.last_message = time.time()

                return parse_response(response)

        except AttributeError:
            logger.warn("Trying to send data without connection")

        except socket.timeout:
            self.disconnect()
            raise ConnectionError("Socket timeout")

        except socket.error as serr:
            self.disconnect()

            if serr.errno == errno.EBADF:
                raise ConnectionError("bad file descriptor")
            elif serr.errno == errno.ECONNREFUSED:
                raise ConnectionError("connection refused")
            elif serr.errno == errno.EPIPE:
                raise ConnectionError("broken pipe")
            elif serr.errno == errno.ECONNRESET:
                raise ConnectionError("connection reset")
            elif serr.errno == errno.ENETUNREACH:
                raise ConnectionError("network unreachable")
            else:
                raise ConnectionError(serr)

        except CameraError:
            raise

        except Exception as e:
            logger.exception(e)
            self.disconnect()
            raise

    def ask_raw(self, command: str):
        with self.lock:
            self.socket.sendall(command.encode("ascii") + b"\n")
            response = self.recv_end(self.socket)

        return response

    def live(self):
        self.ask("set video.play.live 1")
        self.ask("set video.play.step 0")

    def play(self, cine=1, source="ram"):
        try:
            if self.video_play["step"]:
                self.ask("vplay {{cine: {}, step: 0, from: {}}}".format(cine, source))
            else:
                self.ask("vplay {{cine: {}, step: 1, speed: 1, from: {}}}".format(cine, source))
        except CameraError as e:
            logger.warning(e)

    def set_playhead(self, frame):
        if self.protocol == "PH16":
            if frame != self.video_play["fn"] and frame in range(
                int(self.video_play["in"]), int(self.video_play["out"])
            ):
                self.ask("vplay {{fn: {}}}".format(frame))

    def set_in(self, frame):
        if int(frame) < int(self.c1["out"]):
            if self.protocol == "PH16":
                self.ask("vplay {{in: {}}}".format(frame))
            elif self.protocol == "PH7":
                self.ask("vplay {{firstframe: {}}}".format(frame))

            self.ask("set c1.in {}".format(frame))

    def set_out(self, frame):
        if int(frame) > int(self.c1["in"]):
            if self.protocol == "PH16":
                self.ask("vplay {{out: {}}}".format(frame))
            elif self.protocol == "PH7":
                self.ask("vplay {{lastframe: {}}}".format(frame))

            self.ask("set c1.out {}".format(frame))

    def set_value(self, key, value):
        self.ask("set {} {}".format(key, value))

    def save(self):
        self.ask("fsave {{cine: 1, firstframe: {}, lastframe: {}}}".format(self.c1["in"], self.c1["out"]))

    def set_rtc(self, timestamp=None):
        if not timestamp:
            timestamp = time.time()
        if self.protocol == "PH16":
            self.ask("setrtc {{ value: {} }}".format(int(timestamp)))
        elif self.protocol == "PH7":
            self.ask("set hw.rtctime.secs {}".format(int(timestamp)))


class Takes(object):
    def __init__(self, camera):
        self.camera = camera

    def __len__(self):
        return int(self.camera.ask("get mag.takes"))

    def __getitem__(self, index):
        if index >= len(self):
            raise IndexError
        return self.camera.get_takeinfo(
            "fc{}".format(index), ["firstfr", "lastfr", "res", "rate", "trigtime.secs", "format"]
        )


class RamTakes(object):
    def __init__(self, camera):
        self.camera = camera

    def __len__(self):
        if self.camera.protocol == "PH16":
            return int(self.camera.ask("get cam.cines"))
        elif self.camera.protocol == "PH7":
            # disable ram cines for now
            return 0

    def __getitem__(self, index):
        if index >= len(self):
            raise IndexError
        return self.camera.get_takeinfo(
            "c{}".format(index + 1),
            ["state", "firstfr", "lastfr", "res", "rate", "trigtime.secs", "format", "info.serial", "info.name"],
        )
