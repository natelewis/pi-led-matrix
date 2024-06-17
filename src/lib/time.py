import time
import cv2


def get_start_time():
    """
    Returns the current time in seconds.

    Returns:
            int: The current time in seconds.
    """
    return int(time.time())


def ready(start_time, playlist_delay):
    """
    Checks if enough time has passed since the start_time for the playlist_delay.

    Args:
            start_time (int): The start time in seconds.
            playlist_delay (int): The delay in seconds for the playlist.

    Returns:
            bool: True if enough time has passed, False otherwise.
    """
    return bool((int(time.time()) - start_time) < playlist_delay)


def delay(ms):
    """
    Delay the execution for the specified number of milliseconds.

    Parameters:
    - ms (int): The number of milliseconds to delay.

    Returns:
    None
    """
    try:
        cv2.waitKey(ms)
    except:  # pylint: disable=W0702
        time.sleep(ms / 1000)
