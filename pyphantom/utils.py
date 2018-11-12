import logging
import os
import platform
from multiprocessing import Process
from threading import Thread, current_thread

import psutil

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


def get_sys_info():
    mac_os_version = platform.mac_ver()[0]
    memory = psutil.virtual_memory().total / 1024.0 ** 3
    cores = psutil.cpu_count(logical=False)

    return locals()
