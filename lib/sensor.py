import requests
from lib.config import Config
from lib.logger import Logger
from machine import Pin, I2C
import ahtx0
from wifi import WifiHandler

class Sensor:
    temperature_sensor: ahtx0.AHT10 | None = None
    water_sensor: Pin | None = None
    debug: bool = False
    logger: Logger

    def __init__(self, wifi: WifiHandler, config: Config, logger: Logger):
        self.debug = config.debug
        self.logger = logger
        self.api_url = config.api_url
        self.api_token = config.api_token
        self.water_sensor = None
        self.temperature_sensor = None
        self.wifi = wifi
        self.with_temperature_sensor = config.temperature_sensor_enabled
        self.with_water_sensor = config.water_sensor_enabled
        self.temperature_sensor_scl_pin = config.temperature_sensor_scl_pin
        self.temperature_sensor_sda_pin = config.temperature_sensor_sda_pin
        self.water_sensor_in_pin = config.water_sensor_in_pin
        self.water_sensor_out_pin = config.water_sensor_out_pin

        if self.with_water_sensor:
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
                i2c = I2C(
                    scl=Pin(self.temperature_sensor_scl_pin),
                    sda=Pin(self.temperature_sensor_sda_pin),
                )
                self.temperature_sensor = ahtx0.AHT10(i2c)

            return self.temperature_sensor
        except Exception as e:
            self.logger.output(f'Error initializing sensor: {e}')
            return None

    def setup_water_sensor(self):
        self.water_sensor = Pin(
            self.water_sensor_in_pin,
            Pin.IN,
            Pin.PULL_DOWN,
        )

        Pin(
            self.water_sensor_out_pin,
            Pin.OUT,
            value=1,
        )

    def update_data(self):
        self.logger.output('Updating sensor...')

        try:
            data = {
                "address": self.wifi.mac_address,
                "temperature": None,
                "humidity": None,
                "is_wet": None,
            }

            if self.with_temperature_sensor:
                data['temperature'] = self.temperature
                data['humidity'] = self.humidity

            if self.with_water_sensor:
                data['is_wet'] = self.is_wet

            response = requests.post(
                f'{self.api_url}/solar/sensor/details',
                headers={
                    'Authorization': f'Bearer {self.api_token}',
                    'Content-Type': 'application/json',
                },
                json=data,
                timeout=5,
            )

            self.logger.output('Data sent successfully:', response.status_code, response.content)
        except Exception as e:
            self.logger.output(f'Error sending data: {e}')
