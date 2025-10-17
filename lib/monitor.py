import gc
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
    last_updated: int = 0
    debug: bool = False
    reset_seconds: int = 3600

    def __init__(self, config: Config):
        self.debug = config.debug
        self.reset_seconds = config.reset_seconds
        self.with_temperature_sensor = config.temperature_sensor_enabled
        self.with_water_sensor = config.water_sensor_enabled
        self.with_bluetooth = config.bluetooth_enabled

        self.wifi = WifiHandler(config)

        if self.with_bluetooth:
            self.set_bluetooth_devices(config.bluetooth_devices)

            self.bluetooth_state = BluetoothState(self.wifi, config)

        if self.with_temperature_sensor or self.with_water_sensor:
            self.sensor = Sensor(self.wifi, config)

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

            if self.with_bluetooth and self.bluetooth_devices:
                try:
                    self.update_bluetooth()
                except Exception as e:
                    self.output(f'Error updating Bluetooth devices: {e}')

                if self.reset_seconds > 0 and utime.time() - self.last_updated > self.reset_seconds:
                    self.output('No Bluetooth updates in the last hour, restarting.')

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
        self.output('Updating Bluetooth devices...')

        self.bluetooth_state.start()

        self.bluetooth_state.scan()

        wait(lambda: self.bluetooth_state.state == STATE_SCANNING, timeout=15, on_timeout=lambda: self.output('Timeout waiting for scan, stopping scan.'))

        for device_address in self.bluetooth_devices:
            if device_address not in self.bluetooth_state.devices:
                self.output(f'Device {device_address} not found, skipping.')

                continue

            bluetooth_device = self.bluetooth_state.devices[device_address]

            self.bluetooth_state.connect(bluetooth_device)

            connection_state = wait(lambda: self.bluetooth_state.state in [STATE_CONNECTED, STATE_CONNECTING, STATE_DISCOVERING], timeout=15, on_timeout=lambda: self.output('Timeout waiting for connection...'))

            if connection_state is False:
                continue

            if self.bluetooth_state.state in [STATE_CONNECTED, STATE_READY]:
                self.output('Connected and ready!')

                self.bluetooth_state.fetch_data()

                wait(lambda: self.bluetooth_state.state in [STATE_COMMUNICATING], timeout=15, on_timeout=lambda: self.output('Timeout waiting for communication...'))

                self.bluetooth_state.disconnect()

                self.bluetooth_state.save_data(bluetooth_device)

                self.last_updated = utime.time()

            gc.collect()

        # self.bluetooth_state.stop()

    def output(self, *args):
        if not self.debug:
            return

        print('DEBUG:', *args)
