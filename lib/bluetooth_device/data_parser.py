from lib.logger import Logger

class DataParser:
    _partial_payload: bytes | None = None
    cell_voltages = {}
    device_data = {}
    logger: bool = False

    def __init__(self, *, logger: Logger):
        self.logger = logger
        self._partial_payload = None
        self.cell_voltages = {}
        self.device_data = {}

    def decode_prod_date_to_timestamp(self, prod):
        year  = 2000 + (prod >> 9)
        month = (prod >> 5) & 0x0F
        day   = prod & 0x1F

        return (day * 86400) + (month * 2678400) + (year * 31536000)

    def parse_response(self, data: bytes) -> dict:
        self.logger.output('DATA', len(data), data)

        if data[0:2] == b'\xdd\x04':
            cell_count = int(int.from_bytes(data[3:4],'big') / 2)
            response = {
                'voltages': [],
                'cell_count': cell_count,
            }

            i = 4
            n = 0
            while n < cell_count:
                response['voltages'].append(int.from_bytes(data[i:i+2],'big'))

                i += 2
                n += 1

            return response, True

        if data == b'w':
            data = self._partial_payload

            response = {
                'voltage': int.from_bytes(data[4:6], 'big'),
                'current': int.from_bytes(data[6:8], 'big'),
                'ahrem': int.from_bytes(data[8:10],'big'),
                'ahmax': int.from_bytes(data[10:12],'big'),
                # 'cycles': int.from_bytes(data[12:14],'big'),
                # 'production_timestamp': self.decode_prod_date_to_timestamp(int.from_bytes(data[14:16], 'big')),
                'protection_status': int.from_bytes(data[20:22],'big'),
                # 'version': data[22],
                'soc': data[23],
                # 'fet': data[24],
                'cells': data[25],
                # 'temperature_sensors': data[26],
                'temperature': (int.from_bytes(data[27:29],'big') - 2731) * 0.1
            }

            if (response['current'] > 0x7fff):
                response['current'] = response['current'] - 0x10000

            response['watts'] = (response['voltage'] * response['current']) / 10000.0

            self._partial_payload = None

            return response, False

        elif data[0:2] == b'\xdd\x03':
            self._partial_payload = data

            return None, None

        elif self._partial_payload is not None and len(self._partial_payload) > 0:
            self._partial_payload += data

            return None, None

        return None, None
