import gc
import machine
from machine import Pin, I2C
import requests
import sys

from lib.config import Config
from lib.logger import Logger
from thirdparty.ahtx0.ahtx0 import AHT10
from wifi import WifiHandler

class Sensor:
    temperature_sensor: AHT10 | None = None
    water_sensor: Pin | None = None
    debug: bool = False
    logger: Logger

    def __init__(self, wifi: WifiHandler, config: Config, logger: Logger):
        self.debug = config.debug
        self.logger = logger
        self.api_url = config.api_url
        self.api_endpoint = config.sensor_endpoint
        self.config_api_endpoint = config.sensor_config_endpoint
        self.config_last_updated_api_endpoint = config.sensor_config_last_updated_endpoint
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
                self.temperature_sensor = AHT10(I2C(
                    scl=Pin(self.temperature_sensor_scl_pin),
                    sda=Pin(self.temperature_sensor_sda_pin),
                ))

            return self.temperature_sensor

        except OSError as e:
            self.logger.output(f'OSError initializing temperature sensor: {e}')

            machine.reset()

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
            response = requests.post(
                f'{self.api_url}/{self.api_endpoint}',
                headers={
                    'Authorization': f'Bearer {self.api_token}',
                    'Content-Type': 'application/json',
                },
                json={
                    "address": self.wifi.mac_address,
                    "temperature": self.temperature if self.with_temperature_sensor else None,
                    "humidity": self.humidity if self.with_temperature_sensor else None,
                    "is_wet": self.is_wet if self.with_water_sensor else None,
                },
                timeout=10,
            )

            self.logger.output('Data sent successfully:', response.status_code, response.content)

            response.close()

            del response

            gc.collect()

        except OSError as e:
            if str(e.args[0]) != '-116':
                self.logger.output(f'OSError sending sensor data: {e}')
                if self.debug:
                    sys.print_exception(e)

                machine.reset()

        except Exception as e:
            self.logger.output(f'Error sending sensor data: {e}')
            if self.debug:
                sys.print_exception(e)

    def get_config_last_updated_at(self) -> int | None:
        self.logger.output('Fetching config last updated timestamp...')

        try:
            response = requests.get(
                f'{self.api_url}/{self.config_last_updated_api_endpoint}',
                headers={
                    'Authorization': f'Bearer {self.api_token}',
                    'Content-Type': 'application/json',
                },
                json={
                    "address": self.wifi.mac_address,
                },
                timeout=10,
            )

            last_updated_at = None
            if response.status_code == 200:
                json_response = response.json()
                last_updated_at = json_response.get('config_updated_at')

                del json_response

                self.logger.output('Config last updated at:', last_updated_at)

            else:
                self.logger.output('Failed to fetch config last updated timestamp')

            response.close()

            del response

            return last_updated_at

        except OSError as e:
            if str(e.args[0]) != '-116':
                self.logger.output(f'OSError determining whether config needs updating: {e}')
                if self.debug:
                    sys.print_exception(e)

                machine.reset()

        except Exception as e:
            self.logger.output(f'Error determining whether config needs updating: {e}')
            if self.debug:
                sys.print_exception(e)

        return None
