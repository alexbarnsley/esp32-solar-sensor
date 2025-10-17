import network
import utime
import ntptime
from lib.config import Config

class WifiHandler:
    debug: bool = False
    networks: dict[str, str] = {}

    def __init__(self, config: Config):
        self.debug = config.debug

        self.networks = config.wifi_networks

        self.wlan = network.WLAN()
        self.wlan.active(True)

        self.do_connect()

        self.output('synchronizing time with NTP server...')

        ntptime.settime()

        self.output('current time:', utime.localtime())

    @property
    def mac_address(self) -> str:
        mac_address_hex = self.wlan.config('mac').hex()

        return ':'.join(mac_address_hex[i:i+2] for i in range(0,12,2))

    @property
    def is_connected(self) -> bool:
        return self.wlan.isconnected()

    def check_connection(self):
        self.output('checking wifi connection...')
        if not self.wlan.isconnected():
            self.do_connect()

    def do_connect(self):
        self.output('connecting to network...')

        while not self.wlan.isconnected():
            access_points = self.wlan.scan()
            access_points.sort(key=lambda x: x[3], reverse=True)
            access_points = [access_point[0] for access_point in access_points if access_point[0].decode('utf-8') in self.networks]

            for ssid in access_points:
                ssid = ssid.decode('utf-8')
                if self.networks.get(ssid) is None:
                    self.output(f'No password for {ssid}, skipping.')

                    continue

                try:
                    self.wlan.connect(ssid, self.networks[ssid])
                    is_connected = self.wlan.isconnected()
                    attempts = 0

                    self.output(f'Connecting to {ssid}...')
                    while not is_connected and attempts < 10:
                        utime.sleep(1)
                        is_connected = self.wlan.isconnected()
                        attempts += 1

                    if is_connected:
                        break
                except Exception as e:
                    self.output(f'Error connecting to {ssid}: {e}')

        self.output('network config:', self.wlan.ipconfig('addr4'))

    def output(self, *args):
        if not self.debug:
            return

        print('DEBUG:', *args)
