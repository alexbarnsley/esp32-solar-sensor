import gc
import sys
import utime
import machine
from lib.config import Config
from lib.bluetooth_device.bluetooth_state import STATE_COMMUNICATING, STATE_CONNECTED, STATE_CONNECTING, STATE_DISCOVERING, STATE_SCANNING, BluetoothState, STATE_READY
from lib.sensor import Sensor
from lib.utils import wait
from lib.wifi import WifiHandler

class MonitorDevice:
    bluetooth_devices: list[str] = []
    bluetooth_state: BluetoothState
    last_updated: dict[str, int] = 0
    debug: bool = False
    reset_seconds: int = 3600
    config: Config
    sensor: Sensor
    wifi: WifiHandler
    with_bluetooth: bool = False
    with_temperature_sensor: bool = False
    with_water_sensor: bool = False

    def __init__(self, config: Config):
        self.config = config
        self.debug = config.debug
        self.reset_seconds = config.reset_seconds
        self.with_temperature_sensor = config.temperature_sensor_enabled
        self.with_water_sensor = config.water_sensor_enabled
        self.with_bluetooth = config.bluetooth_enabled
        self.last_updated = {}

        self.wifi = WifiHandler(config)

        if self.with_bluetooth:
            self.output('Initializing Bluetooth state...')

            self.bluetooth_state = BluetoothState(self.wifi, config)

            self.set_bluetooth_devices(config.bluetooth_devices)

        if self.with_temperature_sensor or self.with_water_sensor:
            self.output('Initializing Sensor...')

            self.sensor = Sensor(self.wifi, config)

        self.output('MonitorDevice initialized.')

    def set_bluetooth_devices(self, devices: list[str]):
        self.bluetooth_devices = devices
        self.bluetooth_state.only_devices = devices

    def run(self):
        while True:
            self.wifi.check_connection()

            if self.with_temperature_sensor or self.with_water_sensor:
                try:
                    self.sensor.update_data()
                except Exception as e:
                    self.output(f'Error updating sensor data: {e}')
                    if self.debug:
                        sys.print_exception(e)

            if self.with_bluetooth and self.bluetooth_devices:
                try:
                    self.update_bluetooth()
                except Exception as e:
                    self.output(f'Error updating Bluetooth devices: {e}')
                    if self.debug:
                        sys.print_exception(e)

                for device_address in self.bluetooth_devices:
                    last_updated = self.last_updated.get(device_address)
                    if last_updated is None:
                        continue

                    if self.reset_seconds > 0 and utime.time() - last_updated > self.reset_seconds:
                        self.output(f'No bluetooth updates for {device_address} in the last hour, restarting.')

                        machine.reset()

            if self.config.auto_update_enabled and self.config.update_github_repo:
                try:
                    import lib.updater

                    lib.updater.install_update_if_available(
                        self.config.update_github_repo,
                        self.config.update_github_src_dir,
                        main_dir=self.config.update_main_dir,
                        new_version_dir=self.config.update_new_version_dir,
                        config_file='config.json',
                    )
                except Exception as e:
                    self.output(f'Error checking for updates: {e}')
                    if self.debug:
                        sys.print_exception(e)

            gc.collect()

            self.sleep()

    def sleep(self):
        hour = utime.localtime()[3]
        if hour > 9 and hour < 18:
            pause_delay = 10
        else:
            pause_delay = 60

        utime.sleep(pause_delay)

    def update_bluetooth(self):
        self.output('Updating Bluetooth devices...')

        self.bluetooth_state.start()

        self.bluetooth_state.scan()

        wait(lambda: self.bluetooth_state.state == STATE_SCANNING, timeout=15, on_timeout=lambda: self.output('Timeout waiting for scan, stopping scan.'))

        for device_address in self.bluetooth_devices:
            if device_address not in self.bluetooth_state.devices:
                self.output(f'Device {device_address} not found, skipping.')

                continue

            self.output(f'Updating device {device_address}...')

            self.bluetooth_state.connect(device_address)

            connection_state = wait(lambda: self.bluetooth_state.state in [STATE_CONNECTED, STATE_CONNECTING, STATE_DISCOVERING], timeout=15, on_timeout=lambda: self.output('Timeout waiting for connection...'))

            if connection_state is False:
                continue

            if self.bluetooth_state.state in [STATE_CONNECTED, STATE_READY]:
                self.output('Connected and ready!')

                self.bluetooth_state.fetch_data()

                wait(lambda: self.bluetooth_state.state in [STATE_COMMUNICATING], timeout=15, on_timeout=lambda: self.output('Timeout waiting for communication...'))

                self.bluetooth_state.disconnect()

                self.bluetooth_state.save_data(device_address)

                self.last_updated[device_address] = utime.time()

            gc.collect()

        # self.bluetooth_state.stop()

    def output(self, *args):
        if not self.debug:
            return

        print('DEBUG:', *args)
