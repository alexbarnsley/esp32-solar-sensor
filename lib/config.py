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
