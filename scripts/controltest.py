#!/usr/bin/python

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

print("Testing control module methods by enabling all controls")
plant1_control.manage_lights("on")
plant1_control.manage_fan("on")
plant1_control.manage_valve("on")
print("Control cluster contains mask A: " +
      str('{0:b}'.format(ControlCluster.bank_mask[plant1_control.bank])))
print("Turning off plant 1 lights...")
plant1_control.manage_lights("off")
print("Control cluster now contains bank mask " +
      str('{0:b}'.format(ControlCluster.bank_mask[plant1_control.bank])))


print("Sending mask to GPIO Extender Module to test functionality...")
print(
    "Using " + str('{0:b}'.format(ControlCluster.bank_mask[plant1_control.bank])))
i2c_utility.GPIO_update_output(
    bus, plant1_control.IOexpander,
    plant1_control.bank,
    ControlCluster.bank_mask[plant1_control.bank])
print("LEDs 4 and 6 should be turned on.")
sleep(5)

print("Now testing second control module....")
plant2_control.manage_lights("on")
plant2_control.manage_fan("on")
plant2_control.manage_valve("on")
print("Sending command to turn on all control units")
i2c_utility.GPIO_update_output(
    bus, plant2_control.IOexpander,
    plant2_control.bank,
    ControlCluster.bank_mask[plant2_control.bank])
print("All three plant 2 control modules should be on")
sleep(5)
print("Turning off fan module...")
plant2_control.manage_fan("off")
i2c_utility.GPIO_update_output(
    bus, plant2_control.IOexpander,
    plant2_control.bank,
    ControlCluster.bank_mask[plant2_control.bank])
print("The light corresponding to the fan should be off")
sleep(5)

print("Sending duplicate command to test IO efficiency")
i2c_utility.GPIO_update_output(
    bus, plant2_control.IOexpander,
    plant2_control.bank,
    ControlCluster.bank_mask[plant2_control.bank])
