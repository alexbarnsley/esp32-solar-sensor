import utime

def wait_for(condition_func, *, timeout=10, check_interval=0.1, on_timeout=None) -> bool:
    start_time = utime.ticks_ms()
    while not condition_func():
        if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout * 1000:
            if on_timeout:
                on_timeout()

            return False

        utime.sleep(check_interval)

    return True

def copy_file(from_path, to_path):
    with open(from_path) as from_file:
        with open(to_path, 'w') as to_file:
            CHUNK_SIZE = 512 # bytes
            data = from_file.read(CHUNK_SIZE)
            while data:
                to_file.write(data)
                data = from_file.read(CHUNK_SIZE)

            to_file.close()

        from_file.close()
