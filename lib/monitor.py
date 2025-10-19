import gc
import sys
from lib.logger import Logger
import utime
import machine
from lib.config import Config
from lib.bluetooth_device.bluetooth_state import BluetoothState, STATE_CONNECTED, STATE_DISCONNECTED, STATE_IDLE, STATE_SCANNING, STATE_READY
from lib.sensor import Sensor
from lib.utils import wait_for
from lib.wifi import WifiHandler
import lib.updater

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
        self.logger = Logger(self.debug)
        self.reset_seconds = config.reset_seconds
        self.with_temperature_sensor = config.temperature_sensor_enabled
        self.with_water_sensor = config.water_sensor_enabled
        self.with_bluetooth = config.bluetooth_enabled
        self.last_updated = {}

        gc.enable()

        self.wifi = WifiHandler(config, logger=self.logger)

        # We check for updates here once we've established a wifi connection
        self.check_for_updates()

        if self.with_bluetooth:
            self.logger.output('Initializing Bluetooth state...')

            self.bluetooth_state = BluetoothState(self.wifi, config, logger=self.logger)

            self.set_bluetooth_devices(config.bluetooth_devices)

        if self.with_temperature_sensor or self.with_water_sensor:
            self.logger.output('Initializing Sensor...')

            self.sensor = Sensor(self.wifi, config, logger=self.logger)

        self.logger.output('MonitorDevice initialized.')

    def set_bluetooth_devices(self, devices: list[str]):
        self.bluetooth_devices = devices
        self.bluetooth_state.only_devices = devices

    def run(self):
        while True:
            self.wifi.check_connection()

            gc.collect()

            if self.with_temperature_sensor or self.with_water_sensor:
                try:
                    self.sensor.update_data()
                except Exception as e:
                    self.logger.output(f'Error updating sensor data: {e}')
                    if self.debug:
                        sys.print_exception(e)

            gc.collect()

            if self.with_bluetooth and self.bluetooth_devices:
                try:
                    self.update_bluetooth()
                except Exception as e:
                    self.logger.output(f'Error updating Bluetooth devices: {e}')
                    if self.debug:
                        sys.print_exception(e)

                for device_address in self.bluetooth_devices:
                    last_updated = self.last_updated.get(device_address)
                    if last_updated is None:
                        continue

                    if self.reset_seconds > 0 and utime.time() - last_updated > self.reset_seconds:
                        self.logger.output(f'No bluetooth updates for {device_address} in the last hour, restarting.')

                        machine.reset()

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
        self.logger.output('Updating Bluetooth devices...')

        self.bluetooth_state.start()

        self.bluetooth_state.scan()

        wait_for(lambda: self.bluetooth_state.state != STATE_SCANNING, timeout=15, on_timeout=lambda: self.logger.output('Timeout waiting for scan, stopping scan.'))

        for device_address in self.bluetooth_devices:
            if device_address not in self.bluetooth_state.devices:
                self.logger.output(f'Device {device_address} not found, skipping.')

                continue

            self.logger.output(f'Updating device {device_address}...')

            self.bluetooth_state.connect(device_address)

            connection_state = wait_for(
                lambda: self.bluetooth_state.state in [STATE_DISCONNECTED, STATE_READY],
                timeout=15,
                on_timeout=lambda: self.logger.output(f'Timeout waiting for connection... | Device state: {self.bluetooth_state.state}')
            )

            if connection_state is False:
                self.bluetooth_state.disconnect()

                continue

            if self.bluetooth_state.state in [STATE_CONNECTED, STATE_READY]:
                self.logger.output('Connected and ready!')

                self.bluetooth_state.fetch_data()

                wait_for(lambda: self.bluetooth_state.state == STATE_IDLE, timeout=15, on_timeout=lambda: self.logger.output('Timeout waiting for communication...'))

                self.bluetooth_state.disconnect()

                self.bluetooth_state.save_data(device_address)

                self.last_updated[device_address] = utime.time()

            gc.collect()

    def check_for_updates(self):
        if self.config.auto_update_enabled and self.config.update_github_repo:
            try:
                has_updated = lib.updater.install_update_if_available(self.config)

                if has_updated:
                    self.logger.output('Update installed, restarting device...')

                    machine.reset()

            except Exception as e:
                self.logger.output(f'Error checking for updates: {e}')
                if self.debug:
                    sys.print_exception(e)

                machine.reset()

            gc.collect()

            utime.sleep(1)
