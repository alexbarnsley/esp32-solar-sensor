import os

class Config:
    debug: bool
    reset_seconds: int

    last_updated: int

    api_url: str
    api_token: str
    battery_endpoint: str
    sensor_endpoint: str
    sensor_config_endpoint: str

    wifi_networks: dict[str, str]

    bluetooth_enabled: bool
    bluetooth_devices: list[str]

    water_sensor_enabled: bool
    water_sensor_in_pin: int
    water_sensor_out_pin: int

    temperature_sensor_enabled: bool
    temperature_sensor_scl_pin: int
    temperature_sensor_sda_pin: int

    auto_update_enabled: bool
    update_github_repo: str
    update_github_src_dir: str
    update_new_version_dir: str
    update_api_token: str | None

    auto_update_config_enabled: bool
    auto_update_config_url: str | None
    auto_update_config_token: str | None

    def __init__(self, config: dict):
        self.debug = config.get('debug', False)

        self.load_cache(config)

        self.reset_seconds = config.get('reset_seconds', 3600)

        self.api_url = config.get('api', {}).get('url', '').rstrip('/')
        self.api_token = config.get('api', {}).get('token', '')
        self.battery_endpoint = config.get('api', {}).get('battery_endpoint', 'solar/battery/details')
        self.sensor_endpoint = config.get('api', {}).get('sensor_endpoint', 'solar/sensor/details')
        self.sensor_config_endpoint = config.get('api', {}).get('sensor_config_endpoint', 'solar/sensor/config')

        self.wifi_networks = config.get('wifi', {})

        self.bluetooth_enabled = config.get('bluetooth', {}).get('enabled', True)
        self.bluetooth_devices = config.get('bluetooth', {}).get('devices', [])

        self.water_sensor_enabled = config.get('water_sensor', {}).get('enabled', True)
        self.water_sensor_in_pin = config.get('water_sensor', {}).get('in', 0)
        self.water_sensor_out_pin = config.get('water_sensor', {}).get('out', 1)

        self.temperature_sensor_enabled = config.get('temperature_sensor', {}).get('enabled', True)
        self.temperature_sensor_scl_pin = config.get('temperature_sensor', {}).get('scl', 0)
        self.temperature_sensor_sda_pin = config.get('temperature_sensor', {}).get('sda', 1)

        self.auto_update_enabled = config.get('auto_update', {}).get('enabled', True)
        self.update_github_repo = config.get('auto_update', {}).get('github_repo', 'alexbarnsley/esp32-solar-sensor')
        self.update_github_src_dir = config.get('auto_update', {}).get('github_src_dir', '')
        self.update_new_version_dir = config.get('auto_update', {}).get('new_version_dir', 'next')
        self.update_api_token = config.get('auto_update', {}).get('api_token', None)

        self.auto_update_config_enabled = config.get('auto_update', {}).get('config', {}).get('enabled', self.auto_update_enabled)
        self.auto_update_config_token = config.get('auto_update', {}).get('config', {}).get('api_token')
        self.auto_update_config_url = config.get('auto_update', {}).get('config', {}).get('url')

        if self.auto_update_config_url is None or len(self.auto_update_config_url) == 0:
            self.auto_update_config_url = self.api_url + '/' + self.sensor_config_endpoint

            if self.auto_update_config_token is None:
                self.auto_update_config_token = self.api_token

        gc.collect()

    def load_cache(self, config: dict):
        self.last_updated = config.get('cache', {}).get('config_last_updated_at', 0)
        self.version = config.get('cache', {}).get('version', '0.0.0')

    @staticmethod
    def from_json_file(file_path: str) -> 'Config':
        with open('config.default.json', 'r') as f:
            default_config = json.load(f)

        with open(file_path, 'r') as f:
            config_data = json.load(f)

        cache_data = Config.get_cache()

        merged_config = default_config.copy()
        merged_config.update(config_data)

        merged_config['cache'] = cache_data.copy()

        del default_config
        del config_data
        del cache_data

        return Config(merged_config)

    @staticmethod
    def get_cache(key: str | None = None):
        try:
            with open('cache.json', 'r') as f:
                cache_data = json.load(f)
                f.close()

            if key is not None:
                return cache_data.get(key)

            return cache_data

        except OSError as e:
            print(f'OSError reading cache file: {e}')

            machine.reset()

        except Exception:
            return None if key is not None else {}

    def update_cache(self, key: str, value):
        cache_data = Config.get_cache()

        cache_data[key] = value

        with open('cache.json.tmp', 'w') as f:
            f.write(json_dumps_with_indent(cache_data))
            f.close()

        copy_file('cache.json.tmp', 'cache.json')
        os.remove('cache.json.tmp')

        self.load_cache(cache_data)
