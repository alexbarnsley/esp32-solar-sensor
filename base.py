from lib.monitor import MonitorDevice

monitor = MonitorDevice(debug=True)
monitor.set_bluetooth_devices([
    # 'A5:C2:37:2D:C6:6A',
    'A5:C2:37:2D:D9:E4',
    'A5:C2:37:2D:C6:18',
])

monitor.run()
