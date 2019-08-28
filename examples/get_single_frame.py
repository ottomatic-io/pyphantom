from pyphantom.discover import discover
from pyphantom.flex import Phantom
from pyphantom.frame import get_frames
from pyphantom.network import get_networks


def get_single_frame(take_number: int, frame_number: int):
    networks = get_networks()
    cameras = discover(networks)
    c = cameras[0]

    camera = Phantom(c.ip, c.port, c.protocol)
    camera.connect()

    frame_index = int(camera.takes[take_number]["firstfr"]) + frame_number
    frame_data = get_frames(camera=camera, take=take_number, frame_index=frame_index, from_ram=False, count=1)[0]

    # TODO: do something useful with the frame data


if __name__ == "__main__":
    get_single_frame(take_number=0, frame_number=0)
