#!/usr/bin/python

import smbus
import i2c_utility
#import models
#import app
from sensor_models import SensorCluster
bus = smbus.SMBus(1)

plant0 = SensorCluster(ID=0, temp_addr=0x48, humidity_addr=0x00, lux_addr=0x39, lux_mux_chan=0, adc_addr=0x00, mux_addr=0x70)
plant1 = SensorCluster(ID=1, temp_addr=0x48, humidity_addr=0x00, lux_addr=0x39, lux_mux_chan=0, adc_addr=0x00, mux_addr=0x70)
print("Plant sensor clusters have successfully been created with IDs: " + str(plant0.ID) + "," + str(plant1.ID))


print("Updating sensor data...")
if plant0.updateAllSensors(bus) == False:
	print("Plant 0 failed to update.")
if plant1.updateAllSensors(bus) == False:
	print("Plant 1 failed to update")

print("plant0 temperature is " + str(plant0.temp))
print("plant0 lux is " + str(plant0.lux))
print("plant1 lux is " + str(plant1.lux))



