import os
import sys
import json
import time
import random
import ctypes
import logging
import asyncio
import watchfiles
import signal
import pyvda


def get_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("WallpaperRotate.log", encoding="utf-8")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = get_logger()


def set_wallpaper_spi(path: str) -> bool:
    """
    Set wallpaper using SystemParametersInfo
    May only set wallpaper for current virtual desktop on some versions of Windows

    path: path to image file
    return: True if success, False if failed
    """

    SystemParametersInfo = ctypes.windll.user32.SystemParametersInfoW
    SPI_SETDESKWALLPAPER = 0x0014
    result = SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, path, 3)

    return result


def set_wallpaper_vda(path: str) -> bool:
    """
    Set wallpaper using Virtual Desktop Accessor

    path: path to image file
    return: True if success, False if failed
    """
    try:
        pyvda.set_wallpaper_for_all_desktops(path)
        return True
    except Exception as e:
        logger.error(f"set wallpaper failed: {e}")
        return False


windows_version = sys.getwindowsversion()
if windows_version.major >= 10 and windows_version.build >= 21313:
    set_wallpaper = set_wallpaper_vda
else:
    set_wallpaper = set_wallpaper_spi


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_image_list(config) -> list[str]:
    dirs = config["directories"]
    image_list = []
    for directory in dirs:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith((".jpg", ".jpeg", ".png")):
                    image_list.append(os.path.join(root, file))
    return image_list


class WallpaperExecutor:
    """
    executing wallpaper rotation
    """

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def __call__(self):
        self.execute()

    def execute(self):
        try:
            state = load_json("state.json")
            config = load_json("config.json")
        except Exception as e:
            self.logger.error(f"load json failed: {e}")
            return

        last_update = state["last_update"]
        if last_update is not None and time.time() - last_update < config["interval"]:
            self.logger.info(f"interval not reached, skip")
            return

        image_list = get_image_list(config)
        if not image_list:
            self.logger.error(f"image list is empty, check directories in config.json")
            return

        visited: list[str] = state["visited"]
        available_images = list(set(image_list) - set(visited))
        if not available_images:
            visited = []
            available_images = image_list

        image = random.choice(available_images)
        success = set_wallpaper(image)

        if success:
            state["last_update"] = time.time()
            state["visited"].append(image)

            # this will trigger execute_watch_file, but it's okay because "last_update" is updated
            save_json("state.json", state)
            self.logger.info(f"set wallpaper: {image}")
        else:
            self.logger.error(f"set wallpaper failed: {image}")


async def execute_periodically(executor, interval: int):
    while True:
        executor()
        await asyncio.sleep(interval)


async def execute_watch_file(executor, paths: list[str]):
    async for changes in watchfiles.awatch(*paths):
        logger.info(f"watched files changed: {changes}")
        executor()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    pid = os.getpid()
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    save_json("ProcessInfo.json", {"pid": pid, "start_time": start_time})
    logger.info(f"Process start: pid={pid}, start_time={start_time}")

    if not os.path.exists("state.json"):
        save_json("state.json", {"last_update": None, "visited": []})
    if not os.path.exists("config.json"):
        save_json("config.json", {"interval": 3600, "directories": []})
        logger.warning(f"config not found, create an empty one")
        logger.warning(f"please edit config.json to set directories")

    config = load_json("config.json")
    executor = WallpaperExecutor(logger)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = [
        loop.create_task(execute_periodically(executor, min(config["interval"], 600))),
        loop.create_task(execute_watch_file(executor, ["config.json", "state.json"])),
    ]

    loop.run_until_complete(asyncio.wait(tasks))


if __name__ == "__main__":
    main()
