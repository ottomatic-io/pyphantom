from __future__ import print_function, absolute_import

import netifaces
import shlex
import socket
import time
import logging
from collections import namedtuple
from threading import Thread

from pyphantom.flex import Phantom

logger = logging.getLogger()

CameraInfo = namedtuple('CameraInfo', ['ip', 'port', 'protocol', 'hardware_version', 'serial', 'name'])


def discover(networks):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', 0))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.setblocking(0)

    cameras = list()

    for interface, ipv4 in networks.items():
        try:
            s.sendto('phantom?', (ipv4['broadcast'], 7380))
            logger.debug('Sent discovery packet to {}'.format(ipv4['broadcast']))
        except socket.error as e:
            logger.warning('Could not send discovery packet to {}: {}'.format(ipv4['broadcast'], e))

    time.sleep(0.6)

    while True:
        try:
            data, addr = s.recvfrom(1024)
            try:
                protocol, port, hardware_version, serial, name = shlex.split(data.rstrip('\0'))
                name = name.strip('"')
            except ValueError:
                # PH7
                protocol, port = shlex.split(data)
                hardware_version = ''
                serial = ''
                name = ''

            cameras.append(CameraInfo(addr[0], port, protocol, hardware_version, serial, name))

        except socket.error:
            break

    return cameras


def get_networks():
    interfaces = [i for i in netifaces.interfaces() if i.startswith('en')]
    networks = {}
    for interface in interfaces:
        try:
            ipv4 = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]
            logger.debug('{}: ip={}, netmask={}, broadcast={}'.format(interface,
                                                                      ipv4['addr'],
                                                                      ipv4['netmask'],
                                                                      ipv4['broadcast']))
            networks[interface] = ipv4

        except KeyError:
            pass

    return networks


class Cameras(Thread):
    """
    Keeps an updated list of Cameras / CineStations and keeps them connected
    """
    def __init__(self, daemon=True):
        super(Cameras, self).__init__()

        self.daemon = daemon

        self.networks = []
        self.cameras = {}

        self.start()

    def run(self):
        while True:
            networks = get_networks()
            if networks != self.networks:
                logger.info('New network config: %s', networks)
                self.networks = networks

            cameras = discover(self.networks)
            # logger.debug('Discovered %d cameras', len(cameras))

            for camera_info in cameras:
                if camera_info not in self.cameras:
                    logger.info('Connecting to %s', camera_info)
                    camera = Phantom(camera_info.ip, camera_info.port, camera_info.protocol)
                    try:
                        camera.connect()
                        self.cameras[camera_info] = camera
                    except Exception as e:
                        logger.warning(e)

            for camera_info, camera in self.cameras.items():
                try:
                    _ = camera.mag_state
                    time.sleep(0.4)
                except Exception as e:
                    logger.error('Connection dead. %s', e)
                    camera.disconnect()
                    del self.cameras[camera_info]

            # logger.debug('Got %d connected cameras', len(self.cameras))

            time.sleep(.1)

    def __len__(self):
        return len(self.cameras)


if __name__ == '__main__':
    FORMAT = "%(asctime)s %(module)-12s %(levelname)-8s %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.INFO)

    c = Cameras(daemon=False)
