#!/usr/bin/python

import smbus
import i2c_utility
from sensor_models import SensorCluster
from controls import ControlCluster
import sensor_models
#sensor_models.models.lazy_record.connect_db("temp.db")
try:
	bus = smbus.SMBus(1)
except IOError:
	print("Cannot open bus. Ignore if using a virtual environment")


plant1_sense = SensorCluster(ID=1, mux_addr=0x70)
plant2_sense = SensorCluster(ID=2, mux_addr=0x70)
print("Plant sensor clusters have successfully been created with IDs: " +
      str(plant1_sense.ID) + "," + str(plant2_sense.ID))

plant1_control = ControlCluster(1)
plant2_control = ControlCluster(2)
print("Plant control clusters have been created with IDs: " + 
		str(plant1_control.ID) + "," + str(plant2_control.ID))

print("Updating sensor data...")
if plant1_sense.updateAllSensors(bus) == False:
    print("Plant 0 failed to update.")
if plant2_sense.updateAllSensors(bus) == False:
    print("Plant 1 failed to update")

print("plant0 temperature is " + str(plant1_sense.temp))
print("plant0 lux is " + str(plant1_sense.lux))
print("plant1 lux is " + str(plant2_sense.lux))
print("plant humidity is " + str(plant1_sense.humidity))