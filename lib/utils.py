import json
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

def json_dumps_with_indent(data, indent=4, nested_index=1) -> str:
    if not isinstance(data, dict) and not isinstance(data, list):
        return json.dumps(data)

    if len(data) == 0:
        return "{}" if isinstance(data, dict) else "[]"

    output = ''

    is_list = isinstance(data, list)

    if isinstance(data, dict):
        enumerated_data = data.items()
    else:
        enumerated_data = enumerate(data)

    lines = []

    for key, value in enumerated_data:
        indentation = ' ' * (indent * nested_index)
        key_output = ''
        if not is_list:
            key_output = f'"{key}": '

        json_value = json.dumps(value)

        if isinstance(value, dict) or isinstance(value, list):
            json_value = json_dumps_with_indent(value, indent, nested_index + 1)

        lines.append(indentation + key_output + json_value)

    output = (',\n').join(lines)

    return "[\n" + output + "\n" + (' ' * ((nested_index - 1) * indent)) + "]" if is_list else "{\n" + output + "\n" + (' ' * ((nested_index - 1) * indent)) + "}"
