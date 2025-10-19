class Config:
    debug: bool
    reset_seconds: int

    api_url: str
    api_token: str
    solar_endpoint: str
    battery_endpoint: str

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

    def __init__(self, config: dict):
        self.debug = config.get('debug', False)

        self.reset_seconds = config.get('reset_seconds', 3600)

        self.api_url = config.get('api', {}).get('url', '')
        self.api_token = config.get('api', {}).get('token', '')
        self.solar_endpoint = config.get('api', {}).get('solar_endpoint', 'solar/sensor/details')
        self.battery_endpoint = config.get('api', {}).get('sensor_endpoint', 'solar/solar/details')

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

    @staticmethod
    def from_json_file(file_path: str) -> 'Config':
        import json

        with open('config.default.json', 'r') as f:
            default_config = json.load(f)

        with open(file_path, 'r') as f:
            config_data = json.load(f)

        merged_config = default_config.copy()
        merged_config.update(config_data)

        return Config(merged_config)
