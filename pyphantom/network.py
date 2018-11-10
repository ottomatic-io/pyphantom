import logging
import netifaces
import platform
import subprocess

logger = logging.getLogger()


def get_mac(ip):
    if platform.system() != "Windows":
        output = subprocess.check_output(["arp", "-n", ip], universal_newlines=True)
        mac_raw = output.split()[3]
        mac = "".join(["{:02x}".format(int(x, 16)) for x in mac_raw.split(":")])
        return mac
    else:
        output = subprocess.check_output(["arp", "-a", ip])
        return output.splitlines()[3].split()[1].replace(b"-", b"").decode()


def get_interface_of_ip(ip):
    if platform.system() != "Windows":
        output = subprocess.check_output(["/sbin/route", "-n", "get", ip])

        for line in output.splitlines():
            if b"interface" in line:
                return line.split()[1].decode()
    else:
        output = subprocess.check_output(["pathping", "-n", "-w", "1", "-h", "1", "-q", "1", ip])
        interface_ip = output.splitlines()[3].split()[1].decode()
        for name, config in get_networks().items():
            if config["addr"] == interface_ip:
                return name


def get_mac_of_interface(interface):
    try:
        return get_networks()[interface]["mac"]
    except KeyError:
        return None


def get_networks():
    networks = {}
    for interface in netifaces.interfaces():
        try:
            if_addresses = netifaces.ifaddresses(interface)
            config = if_addresses[netifaces.AF_INET][0]
            config["mac"] = if_addresses[netifaces.AF_LINK][0]["addr"].replace(":", "")
            logger.debug(
                "{}: ip={}, netmask={}, broadcast={}, mac={}".format(
                    interface, config["addr"], config["netmask"], config["broadcast"], config["mac"]
                )
            )
            networks[interface] = config

        except KeyError:
            pass

    return networks
