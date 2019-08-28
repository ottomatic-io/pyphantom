from typing import List

from pyphantom.flex import Phantom


def get_frames(camera: Phantom, take: int, frame_index: int, from_ram: bool = False, count: int = 1) -> List[bytes]:
    if camera.protocol == "PH16":
        img_cmd = (
            f"img {{ cine: {take}, start: {frame_index}, "
            f"cnt: {count}, fmt: P10, from: {'ram' if from_ram else 'mag'} }}"
        )
    elif camera.protocol == "PH7":
        img_cmd = f"img {{ cine: {take}, start: {frame_index}, cnt: {count}, fmt: {'P10' if from_ram else 'flash'} }}"
    else:
        raise NotImplementedError

    frame_info = camera.ask(img_cmd)

    if frame_info["fmt"] in ["P10", "266"]:
        width, height = [int(x) for x in frame_info["res"].split("x")]
        frame_size = width * height * 10 // 8

    elif frame_info["fmt"] in ["513", "514", "515", "516", "517"]:
        frame_size = int(camera.ask("get fc{}.frsize".format(take)))

    else:
        raise NotImplementedError

    frames = camera.recvall(frame_size * count)
    return [frames[i : i + frame_size] for i in range(0, len(frames), frame_size)]
