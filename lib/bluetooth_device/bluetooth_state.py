import utime
import requests
import bluetooth

from lib.config import Config
from lib.logger import Logger
from lib.bluetooth_device.bluetooth_device import BluetoothDevice
import lib.bluetooth_device.const as const
from lib.bluetooth_device.data_parser import DataParser

from lib.wifi import WifiHandler

STATE_DISCONNECTED = 'disconnected'
STATE_IDLE = 'idle'
STATE_SCANNING = 'scanning'
STATE_CONNECTING = 'connecting'
STATE_CONNECTED = 'connected'
STATE_DISCOVERING = 'discovering'
STATE_COMMUNICATING = 'communicating'
STATE_READY = 'ready'

class BluetoothState:
    current_device: BluetoothDevice | None = None
    state: str = STATE_DISCONNECTED
    devices: dict[str, BluetoothDevice] = {}
    conn_handle: int | None = None
    services_range: tuple[int, int] | None = None
    data_parser: DataParser = None
    wifi: WifiHandler = None
    bt: bluetooth.BLE = None
    api_url: str = ''
    api_token: str = ''
    state_mapping: dict[str, callable] = {}
    is_started: bool = False
    debug: bool = False
    logger: Logger

    def __init__(self, wifi: WifiHandler, config: Config, logger: Logger):
        self.state_mapping = {
            STATE_CONNECTED: self.on_connected,
        }

        self.is_started = False
        self.debug = config.debug
        self.logger = logger

        self.only_devices = config.bluetooth_devices
        self.wifi = wifi
        self.api_url = config.api_url
        self.api_token = config.api_token
        self.data_parser = DataParser(logger=self.logger)
        self.services_range = None
        self.devices: list[str] = []
        self.conn_handle = None
        self.current_device = None
        self.state = STATE_DISCONNECTED

        self.logger.output('Initializing Bluetooth...')

        self.bt = bluetooth.BLE()

        utime.sleep_ms(100)

        self.bt.irq(self.bt_irq)

        utime.sleep_ms(100)

        self.bt.active(True)

        self.logger.output('Bluetooth initialized.')

    def start(self):
        if self.is_started:
            return

        self.is_started = True
        self.bt.active(True)
        self.set_state(STATE_DISCONNECTED)

    def stop(self):
        self.logger.output('Stopping Bluetooth...')

        if not self.is_started:
            return

        self.is_started = False
        self.bt.active(False)
        self.set_state(STATE_DISCONNECTED)

    def scan(self, duration_seconds: int | float = 5, trigger_microsecond: int = 3000000):
        self.set_state(STATE_SCANNING)
        self.bt.gap_scan(duration_seconds * 1000, trigger_microsecond, trigger_microsecond)

    def connect(self, address: str):
        if self.current_device:
            self.disconnect()

        self.current_device = BluetoothDevice(address)
        self.set_state(STATE_CONNECTING)
        self.bt.gap_connect(0, bytes(int(b, 16) for b in address.split(':')))

    def on_connected(self, data: tuple | None = None):
        self.logger.output('Connected!', data, self.__dict__)
        self.conn_handle = data[0]

        self.get_services()

    def disconnect(self):
        if not self.current_device:
            self.set_state(STATE_DISCONNECTED)

            return

        if self.conn_handle is not None:
            try:
                self.enable_notifications(False)
                self.bt.gap_disconnect(self.conn_handle)
            except Exception as e:
                if str(e) != '-128': # Ignore "already disconnected" error
                    self.logger.output('Error during disconnect:', str(e))

        self.current_device.disconnect()

        self.current_device = None

        utime.sleep_ms(1000)

        self.set_state(STATE_DISCONNECTED)

    def get_services(self):
        if self.current_device:
            self.set_state(STATE_DISCOVERING)

            self.bt.gattc_discover_services(self.conn_handle)

    def get_descriptors(self):
        if self.current_device:
            self.set_state(STATE_DISCOVERING)

            if self.services_range is not None:
                self.bt.gattc_discover_descriptors(self.conn_handle, self.services_range[0], self.services_range[1])
            else:
                self.logger.output('No services found to get descriptors from')

    def set_state(self, state: str, data: tuple | None = None):
        if self.state != state:
            self.logger.output(f'State changed to: {state}')

        self.state = state

        if self.state_mapping.get(state):
            self.state_mapping[state](data)

    def handle_scan_result(self, data: tuple):
        addr_type, addr, adv_type, rssi, ___ = data
        addr_str = ':'.join(['%02X' % i for i in addr])

        if self.only_devices and addr_str not in self.only_devices:
            return

        if addr_str not in self.devices:
            self.devices.append(addr_str)

            self.logger.output('Found device:', addr_str, 'RSSI:', rssi, 'Adv Type:', adv_type, 'Addr Type:', addr_type)

    def handle_service_result(self, data: tuple):
        conn_handle, start_handle, end_handle, uuid = data

        self.logger.output('Service:', uuid, type(uuid), f'{uuid}')
        self.logger.output('  start_handle:', start_handle)
        self.logger.output('  end_handle:', end_handle)

        if uuid == bluetooth.UUID(0xff00):
            self.services_range = (start_handle, end_handle)

            self.get_characteristics(conn_handle, start_handle, end_handle)

    def get_characteristics(self, conn_handle: int, start_handle: int, end_handle: int):
        self.bt.gattc_discover_characteristics(conn_handle, start_handle, end_handle)

    def handle_characteristic_result(self, data: tuple):
        _, end_handle, value_handle, properties, uuid = data

        self.logger.output('characteristic:', uuid, type(uuid), f'{uuid}')
        self.logger.output('  end_handle:', end_handle)
        self.logger.output('  value_handle:', value_handle)
        self.logger.output('  properties:', properties)

        if uuid == bluetooth.UUID(0xff01):
            self.current_device.set_notify_handle(value_handle)
        elif uuid == bluetooth.UUID(0xff02):
            self.current_device.set_write_handle(value_handle)
        elif uuid == bluetooth.UUID(0x2902):
            self.current_device.set_cccd_handle(value_handle)

    def handle_descriptor_result(self, data: tuple):
        _, handle, uuid = data

        self.logger.output('descriptor:', uuid, type(uuid), f'{uuid}')
        self.logger.output('  handle:', handle)

        if uuid == bluetooth.UUID(0x2902):
            self.current_device.set_cccd_handle(handle)

    def handle_services_done(self):
        if not self.current_device:
            return

        if not self.current_device.cccd_handle:
            # self.bt.gattc_discover_descriptors(self.conn_handle, self.services_range[0], self.services_range[1])
            self.get_descriptors()

            return

        if not self.current_device.notify_handle or not self.current_device.write_handle:
            raise Exception('Missing notify or write handle!')

        self.set_state(STATE_READY)

    def handle_descriptor_done(self):
        if not self.current_device:
            return

        if not self.current_device.notify_handle:
            raise Exception('Missing notify handle!')
        elif not self.current_device.write_handle:
            raise Exception('Missing write handle!')
        elif not self.current_device.cccd_handle:
            raise Exception('Missing CCCD handle!')

        self.set_state(STATE_READY)

    def handle_notify(self, data: tuple):
        _, value_handle, notify_data = data

        if value_handle != self.current_device.notify_handle:
            self.logger.output('Notification from unknown handle:', value_handle)

            return

        self.logger.output('Notification from handle:', value_handle, 'data:', "".join(["%02X" % i for i in notify_data]))

        (response, is_voltages) = self.data_parser.parse_response(bytes(notify_data))

        if is_voltages:
            self.logger.output('cell_voltages', response)

            self.data_parser.cell_voltages[self.current_device.address] = response['voltages']
        elif response is not None:
            self.logger.output('response', response)

            self.data_parser.device_data[self.current_device.address] = response

            self.set_state(STATE_IDLE)


            # if self.wifi.is_connected:
            #     post_data = {
            #         'voltage': response.get('voltage', -1),
            #         'current': response.get('current', -1),
            #         'ahrem': response.get('ahrem', -1),
            #         'ahmax': response.get('ahmax', -1),
            #         # 'cycles': response.get('cycles', -1),
            #         # 'production_timestamp': response.get('production_timestamp', -1),
            #         'protection_status': response.get('protection_status', -1),
            #         # 'version': response.get('version', -1),
            #         'soc': response.get('soc', -1),
            #         # 'fet': response.get('fet', -1),
            #         'cells': response.get('cells', -1),
            #         # 'temperature_sensors': response.get('temperature_sensors', -1),
            #         'temperature': response.get('temperature', -1),
            #         'address': self.current_device.address,
            #     }

            #     if self.current_device.address in self.data_parser.cell_voltages:
            #         post_data['cell_voltages'] = self.data_parser.cell_voltages[self.current_device.address]

            #     api_response = requests.post(
            #         f'{self.api_url}/solar/battery/details',
            #         headers={
            #             'Authorization': f'Bearer {self.api_token}',
            #             'Content-Type': 'application/json',
            #         },
            #         json=post_data,
            #         timeout=5,
            #     )

            #     self.logger.output('Data sent successfully:', api_response.status_code, api_response.content)

            #     self.set_state(STATE_IDLE)

            #     if self.current_device.address in self.data_parser.cell_voltages:
            #         del self.data_parser.cell_voltages[self.current_device.address]

    def save_data(self, address: str) -> bool:
        if not self.wifi.is_connected:
            return False

        device_data = self.data_parser.device_data.get(address)
        if not device_data:
            return False

        post_data = {
            'voltage': device_data.get('voltage', -1),
            'current': device_data.get('current', -1),
            'ahrem': device_data.get('ahrem', -1),
            'ahmax': device_data.get('ahmax', -1),
            # 'cycles': device_data.get('cycles', -1),
            # 'production_timestamp': device_data.get('production_timestamp', -1),
            'protection_status': device_data.get('protection_status', -1),
            # 'version': device_data.get('version', -1),
            'soc': device_data.get('soc', -1),
            # 'fet': device_data.get('fet', -1),
            'cells': device_data.get('cells', -1),
            # 'temperature_sensors': device_data.get('temperature_sensors', -1),
            'temperature': device_data.get('temperature', -1),
            'address': address,
        }

        if address in self.data_parser.cell_voltages:
            post_data['cell_voltages'] = self.data_parser.cell_voltages[address]

            del self.data_parser.cell_voltages[address]

        api_response = requests.post(
            f'{self.api_url}/solar/battery/details',
            headers={
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json',
            },
            json=post_data,
            timeout=5,
        )

        self.logger.output('Data sent successfully:', api_response.status_code, api_response.content)

        return True

    def enable_notifications(self, enable: bool = True):
        if not self.current_device:
            return

        if self.current_device.cccd_handle:
            self.logger.output('Triggering notifications:', 'enable' if enable else 'disable')

            self.write_data(b'\x01\x00' if enable else b'\x00\x00', handle=self.current_device.cccd_handle)

            utime.sleep_ms(500)

    def fetch_data(self):
        if not self.current_device:
            return

        self.set_state(STATE_COMMUNICATING)

        self.enable_notifications(True)

        if self.current_device.write_handle:
            self.logger.output('Fetching data...')
            self.write_data(b'\xdd\xa5\x04\x00\xff\xfc\x77')

            utime.sleep_ms(1000)

            self.write_data(b'\xdd\xa5\x03\x00\xff\xfd\x77')

    def write_data(self, data: bytes, *, handle: int | None = None):
        if not self.current_device:
            return

        if handle is None:
            handle = self.current_device.write_handle

        if handle:
            self.logger.output(f'Writing "{"".join(["%02X" % i for i in data])}" to handle {handle}...')
            self.bt.gattc_write(
                self.conn_handle,
                handle,
                data,
                0
            )

    def bt_irq(self, event, data):
        if event == const.IRQ_SCAN_RESULT:
            self.handle_scan_result(data)

        elif event == const.IRQ_SCAN_DONE:
            self.set_state(STATE_IDLE, data)

        elif event == const.IRQ_PERIPHERAL_CONNECT:
            self.set_state(STATE_CONNECTED, data)

        elif event == const.IRQ_GATTC_SERVICE_RESULT:
            self.handle_service_result(data)

        elif event == const.IRQ_GATTC_SERVICE_DONE:
            # self.set_state(STATE_READY)
            self.handle_services_done()

        elif event == const.IRQ_GATTC_CHARACTERISTIC_RESULT:
            self.handle_characteristic_result(data)

        elif event == const.IRQ_GATTC_DESCRIPTOR_RESULT:
            self.handle_descriptor_result(data)

        elif event == const.IRQ_GATTC_DESCRIPTOR_DONE:
            self.handle_descriptor_done()

        elif event == const.IRQ_GATTC_NOTIFY:
            self.handle_notify(data)

        elif event == const.IRQ_PERIPHERAL_DISCONNECT:
            self.logger.output('received disconnect event')

            self.disconnect()

        # else:
        #     self.logger.output('Unhandled event:', event, data)
