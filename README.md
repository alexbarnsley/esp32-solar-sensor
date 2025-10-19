# ESP32-C3 Solar Monitor

This package is used (by myself) with the ESP32-C3 module.

## Setup

1. Pull a copy of the library to your machine:

`git clone --recurse-submodules https://github.com/alexbarnsley/esp32-solar-sensor.git`

2. Create a copy of the default config file:

```
cd esp32-solar-sensor
cp config.default.json config.json
```

3. Edit the new `config.json` values to suit your needs

## Config

There is a [default config file](./config.default.json) - this can be used as a basis to create a `config.json` file which is used for the device.

### debug

Only used when debugging the device. Outputs various information when running

### bluetooth

#### bluetooth.enabled

Used to determine whether the bluetooth is running

#### bluetooth.devices

A list of mac addresses for the device to connect to

### wifi

An object of WiFi networks to connect to. Allows multiple and tries to connect in order of WiFi distance from the device.

In the format of:

```json
{
    "SSID": "password"
}
```

### api

#### api.url

The Base URL to send the device data to.

#### api.token

The API token to use when sending data.

#### api.solar_endpoint

The endpoint used for sending solar battery data. In the format of:

```json
{
    "voltage": 1132,
    "current": 123,
    "ahrem": 800,
    "ahmax": 1000,
    "protection_status": 0,
    "soc": 80,
    "cells": 4,
    "temperature": 134,
    "address": "AA:BB:CC:DD:EE:01",
    "cell_voltages": [321, 321, 321, 321],
}
```

#### api.sensor_endpoint

The endpoint used for sending temperature, humidity, and "is wet" data. In the format of:

```json
{
    "temperature": 24.5,
    "humidity": 44.5,
    "is_wet": false
}
```

### reset_seconds

How long to wait before resetting the device in the event of no bluetooth data being updated. Ignored if the value is `0` or `bluetooth.enabled` is `false`.

### temperature_sensor

#### temperature_sensor.enabled

Whether the temperature sensor is enabled.

#### temperature_sensor.scl

The device Pin number which is connected to the AHTX0 SCL pin.

#### temperature_sensor.sda

The device Pin number which is connected to the AHTX0 SDA pin.

### water_sensor

#### water_sensor.enabled

Whether the water sensor is enabled.

#### water_sensor.in

The device Pin number which is connected to the positive water sensor pin.

#### water_sensor.out

The device Pin number which is connected to the negative water sensor pin.

### auto_update

#### auto_update.enabled

Whether to perform auto-updates.

Default: `true`

#### auto_update.github_repo

The GitHub repository used to check for updates.

Default: `'alexbarnsley/esp32-solar-sensor'`

#### auto_update.github_src_dir

Path within GitHub repository if not the base path.

Default: `''`

#### auto_update.new_version_dir

Directory used to download updates to.

Default: `'next'`

## Hardware

Below is the hardware used with this device:

Device:

- ESP32-C3 (with WiFi and Bluetooth)
- AHTX0 Temperature Sensor
- Generic 2-pin Water Sensor

Solar (in my case):

- 2x Bluetooth LiPo4 12v 100Ah batteries (EcoWorthy)
