def wait(condition_func, *, timeout=10, check_interval=0.1, on_timeout=None) -> bool:
    import utime

    start_time = utime.ticks_ms()
    while condition_func():
        if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout * 1000:
            if on_timeout:
                on_timeout()

            return False

        utime.sleep(check_interval)

    return True
