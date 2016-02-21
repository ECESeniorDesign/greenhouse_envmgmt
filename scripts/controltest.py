#!/usr/bin/python

import sys
sys.path.append("/home/pi/git/greenhouse-webservice/")
import smbus
import i2c_utility
from sensor_models import SensorCluster
from controls import ControlCluster
import sensor_models
from time import sleep
# sensor_models.models.lazy_record.connect_db("temp.db")
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

print("Testing Control Cluster dictionary knowledge...")
print("There are " + str(len(ControlCluster.GPIOdict)) + " control modules")
print("Plant 1 has dictionary " +
      str(ControlCluster.GPIOdict[plant1_control.ID - 1]))


print("Testing controls API")

list1_on = ["light", "fan"]
list2_on = ["light"]
plant1_control.control(bus, on=list1_on)
plant2_control.control(bus, on=list2_on)
print("Module 1 has it's light and fan on.")
print("Module 2 has it's light on")
sleep(2)
plant1_control.control(bus, off="light")
print("Module 1's light has been turned off.")
sleep(2)
print("Sending duplicate command to test efficiency.")
plant1_control.control(bus, off="light")
print("Testing pump operation.")
plant1_control.control(bus, on="pump")
plant2_control.control(bus, on="pump")
sleep(2)
print("Turning off the pump")
plant1_control.control(bus, off="pump")
plant2_control.control(bus, off="pump")
sleep(2)
print("Turning off all devices")
plant1_control.control(bus, off="all")
plant2_control.control(bus, off="all")
