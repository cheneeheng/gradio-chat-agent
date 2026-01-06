from time import sleep


def throttle_if_needed(limit_type: str):
    if limit_type == "rate.minute":
        sleep(2)
    elif limit_type == "rate.hour":
        sleep(5)
