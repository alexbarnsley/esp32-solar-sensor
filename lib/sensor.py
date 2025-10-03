import requests
from machine import Pin, I2C
import ahtx0
from wifi import WifiHandler

class Sensor:
    temperature_sensor: ahtx0.AHT10 | None = None
    water_sensor: Pin | None = None
    debug: bool = False

    def __init__(self, wifi: WifiHandler, *, api_url: str, api_token: str, debug: bool = False):
        self.debug = debug
        self.api_url = api_url
        self.api_token = api_token
        self.water_sensor = None
        self.temperature_sensor = None
        self.wifi = wifi

        self.setup_water_sensor()

    @property
    def is_wet(self) -> bool:
        return self.water_sensor.value() == 1

    @property
    def temperature(self):
        sensor = self.get_temperature_sensor()

        return sensor.temperature if sensor else -1

    @property
    def humidity(self):
        sensor = self.get_temperature_sensor()

        return sensor.relative_humidity if sensor else -1

    def get_temperature_sensor(self):
        try:
            if self.temperature_sensor is None:
                # I2C for the Wemos D1 Mini with ESP8266
                i2c = I2C(scl=Pin(9), sda=Pin(8))
                self.temperature_sensor = ahtx0.AHT10(i2c)

            return self.temperature_sensor
        except Exception as e:
            self.output(f'Error initializing sensor: {e}')
            return None

    def setup_water_sensor(self):
        self.water_sensor = Pin(0, Pin.IN, Pin.PULL_DOWN)
        Pin(1, Pin.OUT, value=1)

    def update_data(self):
        self.output('Updating sensor...')

        try:
            response = requests.post(
                f'{self.api_url}/solar/sensor/details',
                headers={
                    'Authorization': f'Bearer {self.api_token}',
                    'Content-Type': 'application/json',
                },
                json={
                    'address': self.wifi.mac_address,
                    'temperature': self.temperature,
                    'humidity': self.humidity,
                    'is_wet': self.is_wet,
                },
                timeout=5,
            )

            self.output('Data sent successfully:', response.status_code, response.content)
        except Exception as e:
            self.output(f'Error sending data: {e}')

    def output(self, *args):
        if not self.debug:
            return

        print('DEBUG:', *args)
