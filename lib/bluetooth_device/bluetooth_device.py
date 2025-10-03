# from lib.bluetooth_state import bluetooth_state

class BluetoothDevice:
    # conn_handle: int
    address: str
    write_handle: int
    notify_handle: int
    cccd_handle: int

    def __init__(self, address: str):
        self.address = address
        self.write_handle = None
        self.notify_handle = None
        self.cccd_handle = None

    def set_write_handle(self, handle: int):
        self.write_handle = handle

    def set_notify_handle(self, handle: int):
        self.notify_handle = handle

    def set_cccd_handle(self, handle: int):
        self.cccd_handle = handle

    def disconnect(self):
        self.write_handle = None
        self.notify_handle = None
        self.cccd_handle = None

    # def trigger(self, state: str, **kwargs):
    #     if hasattr(self, f'on_{state}'):
    #         getattr(self, f'on_{state}')(**kwargs)

    # def on_connected(self, conn_handle: int):
    #     self.conn_handle = conn_handle

    #     print(f'Connected to device: {self.address.hex(":")}')

    #     # self.get_services()

    # # def get_services(self):
    # #     bluetooth_state.
