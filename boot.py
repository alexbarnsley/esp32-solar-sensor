# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

import utime

print('Starting...')

utime.sleep(30)

import base
#import test_wifi
