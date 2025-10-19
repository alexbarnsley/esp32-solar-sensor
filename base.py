import machine
import sys

from lib.monitor import MonitorDevice
from lib.config import Config

try:
    config = Config.from_json_file('config.json')

    monitor = MonitorDevice(config)

    monitor.run()
except OSError as e:
    print('Fatal error:', e)
    sys.print_exception(e)

    machine.reset()
