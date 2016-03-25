#!/usr/bin/python

import sys
sys.path.append("/home/pi/git/greenhouse-webservice/")
sys.path.append("/home/pi/git/greenhouse_envmgmt/greenhouse_envmgmt")
import smbus
import i2c_utility
from sense import SensorCluster
from control import ControlCluster
from time import sleep
# sensor_models.models.lazy_record.connect_db("temp.db")
try:
    ControlCluster.bus = smbus.SMBus(1)
except IOError:
    print("Cannot open bus. Ignore if using a virtual environment")

plant1_control = ControlCluster(1)
print("Plant control clusters have been created with IDs: " +
      str(plant1_control.ID))

print("Testing Control Cluster dictionary knowledge...")
print("There are " + str(len(ControlCluster.GPIOdict)) + " control modules")
print("Plant 1 has dictionary " +
      str(ControlCluster.GPIOdict[plant1_control.ID - 1]))


print("Testing controls API")

list1_on = ["light", "fan"]
plant1_control.control(on=list1_on)
print("Module 1 has it's light and fan on.")
sleep(2)
plant1_control.control(off="light")
print("Module 1's light has been turned off.")
sleep(2)
print("Sending duplicate command to test efficiency.")
plant1_control.control(off="light")
print("Testing pump operation.")
plant1_control.control(on="pump")
sleep(2)
print("Turning off the pump")
plant1_control.control(off="pump")
sleep(2)
print("Turning off all devices")
plant1_control.control(off="all")
