import network
import utime
import ntptime

WIFI_OPTIONS = {
    'VM4721320': 'h5fGqctyddjc',
    'Tenda_5DEF3C': 'soul3334',
}

class WifiHandler:
    debug: bool = False

    def __init__(self, *, debug: bool = False):
        self.debug = debug
        self.wlan = network.WLAN()
        self.wlan.active(True)

        self.do_connect()

        ntptime.settime()

    @property
    def mac_address(self) -> str:
        mac_address_hex = self.wlan.config('mac').hex()

        return ':'.join(mac_address_hex[i:i+2] for i in range(0,12,2))

    @property
    def is_connected(self) -> bool:
        return self.wlan.isconnected()

    def check_connection(self):
        if not self.wlan.isconnected():
            self.do_connect()

    def do_connect(self):
        self.output('connecting to network...')

        while not self.wlan.isconnected():
            access_points = self.wlan.scan()
            access_points.sort(key=lambda x: x[3], reverse=True)  # Sort by signal strength
            access_points = [access_point[0] for access_point in access_points if access_point[0].decode('utf-8') in WIFI_OPTIONS]

            for ssid in access_points:
                ssid = ssid.decode('utf-8')
                if WIFI_OPTIONS.get(ssid) is None:
                    self.output(f'No password for {ssid}, skipping.')

                    continue

                try:
                    self.wlan.connect(ssid, WIFI_OPTIONS[ssid])
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
