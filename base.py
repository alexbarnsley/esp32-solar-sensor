from lib.monitor import MonitorDevice
from lib.config import Config

config = Config.from_json_file('config.json')

monitor = MonitorDevice(config)

monitor.run()
