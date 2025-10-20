import machine
import network
import ntptime
import utime

from lib.config import Config
from lib.logger import Logger

class WifiHandler:
    debug: bool = False
    networks: dict[str, str] = {}
    logger: Logger

    def __init__(self, config: Config, logger: Logger):
        self.debug = config.debug
        self.logger = logger

        self.networks = config.wifi_networks

        self.wlan = network.WLAN()
        self.wlan.active(True)

        self.do_connect()

        self.logger.output('synchronizing time with NTP server...')

        ntp_counter = 0
        while True:
            try:
                ntptime.settime()

                break

            except OSError as e:
                self.logger.output(f'OSError setting time: {e}')

                machine.reset()

            except Exception as e:
                self.logger.output(f'Error setting time: {e}, retrying in 5 seconds...')

                utime.sleep(5)

            ntp_counter += 1
            if ntp_counter >= 5:
                self.logger.output('Failed to synchronize time after multiple attempts, proceeding without accurate time.')

                machine.reset()

        self.logger.output('current time:', utime.localtime())

    @property
    def mac_address(self) -> str:
        mac_address_hex = self.wlan.config('mac').hex()

        return ':'.join(mac_address_hex[i:i+2] for i in range(0,12,2))

    @property
    def is_connected(self) -> bool:
        return self.wlan.isconnected()

    def check_connection(self):
        self.logger.output('checking wifi connection...')
        if not self.wlan.isconnected():
            self.do_connect()

    def do_connect(self):
        self.logger.output('connecting to network...')

        while not self.wlan.isconnected():
            access_points = self.wlan.scan()
            access_points.sort(key=lambda x: x[3], reverse=True)
            filtered_access_points = {
                access_point[0]: access_point[3]
                for access_point in access_points if access_point[0].decode('utf-8') in self.networks
            }

            del access_points

            if len(filtered_access_points) == 0:
                self.logger.output('No known access points found, retrying...')

                utime.sleep(1)

                continue

            self.logger.output(f'Found {len(filtered_access_points)} access points')

            for ssid, rssi in filtered_access_points.items():
                ssid = ssid.decode('utf-8')
                if self.networks.get(ssid) is None:
                    self.logger.output(f'No password for {ssid}, skipping.')

                    continue

                try:
                    self.logger.output(f'Connecting to {ssid} [RSSI: {rssi}]...')

                    self.wlan.disconnect()

                    utime.sleep(1)

                    self.wlan.connect(ssid, self.networks[ssid])
                    is_connected = self.wlan.isconnected()
                    attempts = 0

                    while not is_connected and attempts < 10:
                        utime.sleep(1)
                        is_connected = self.wlan.isconnected()
                        attempts += 1

                    if is_connected:
                        break

                except OSError as e:
                    self.logger.output(f'OSError connecting to {ssid}: {e}')

                    machine.reset()

                except Exception as e:
                    self.logger.output(f'Error connecting to {ssid}: {e}')

            del filtered_access_points

        self.logger.output('network config:', self.wlan.ipconfig('addr4'))
