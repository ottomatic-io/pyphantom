import logging
import os
import platform
import subprocess
from multiprocessing import Process
from threading import Thread, current_thread

import psutil
import timeout_decorator

logger = logging.getLogger()


class ChildThread(Thread):
    def __init__(self, *args, **kwargs):
        self.parent_thread = current_thread()
        Thread.__init__(self, *args, **kwargs)


def threaded(fn):
    def wrapper(*args, **kwargs):
        t = ChildThread(target=fn, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()

    return wrapper


def processed(fn):
    def wrapper(*args, **kwargs):
        p = Process(target=fn, args=args, kwargs=kwargs)
        p.daemon = True
        p.start()

    return wrapper


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


@timeout_decorator.timeout(5, use_signals=False)
def files_in_use(path, ignore=None):
    if ignore is None:
        ignore = []

    processes = {}

    try:
        logger.info("Checking open files of {}".format(path))
        subprocess.call(["/usr/sbin/lsof", "-l", "-P", "-n", "-F", "cn0", "+c", "0", "+D", path])
    except subprocess.CalledProcessError as e:
        for line in e.output.decode("utf-8").splitlines():
            fields = {f[:1]: f[1:] for f in line.split(b"\0") if f.rstrip(b"\n")}
            if "p" in fields:
                process_name = fields["c"]
                processes[process_name] = set()
            if "n" in fields:
                processes[process_name].add(os.path.basename(fields["n"]))

    for i in ignore:
        processes.pop(i, None)

    return processes


def get_sys_info():
    mac_os_version = platform.mac_ver()[0]
    memory = psutil.virtual_memory().total / 1024.0 ** 3
    cores = psutil.cpu_count(logical=False)

    return locals()
