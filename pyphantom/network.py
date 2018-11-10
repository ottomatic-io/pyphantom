import logging
import netifaces
import platform
import subprocess

logger = logging.getLogger()


def get_mac(ip):
    if platform.system() != "Windows":
        mac_raw = subprocess.check_output("arp -n {} | cut -d ' ' -f4".format(ip, ip), shell=True).strip()
        mac = "".join(["{:02x}".format(int(x, 16)) for x in mac_raw.split(":")])
        return mac
    else:
        output = subprocess.check_output(["arp", "-a", ip])
        return output.splitlines()[3].split()[1].replace("-", "")


def get_interface_of_ip(ip):
    if platform.system() != "Windows":
        output = subprocess.check_output(["/sbin/route", "-n", "get", ip])

        for line in output.splitlines():
            if "interface" in line:
                return line.split()[1]
    else:
        output = subprocess.check_output(["pathping", "-n", "-w", "1", "-h", "1", "-q", "1", ip])
        interface_ip = output.splitlines()[3].split()[1]
        for name, config in get_networks().iteritems():
            if config["addr"] == interface_ip:
                return name


def get_mac_of_interface(interface):
    return get_networks()[interface]["mac"]


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
