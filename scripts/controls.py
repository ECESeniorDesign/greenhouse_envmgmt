#!/usr/bin/python

"""
Pin mapping list
	pumpPin = 11
	fan1Pin = 13
	fan2Pin = 16
	light1Pin = 15
	light2Pin = 12
"""
from i2c_utility import GPIO_out, get_ADC_value, GPIO_add_to_mask
from operator import itemgetter


class ControlCluster(object):
    IOexpander = 0x20  # Address of IO expander module
    GPIOdict = []
    bank_mask = [0, 0]  # Masks to push to IO module
    pumpPin = 0
    pumpBank = 0
    pumpOperation = [0, 0]

    def __init__(self, ID, sensor, ideals):
        self.ID = ID
        self.sensor = sensor # This should be the SensorCluster object
        self.ideals = ideals # List of ideal values from database
        form_GPIO_map()

    def form_GPIO_map(self):
        """ This method creates a dictionary to map plant IDs to
        GPIO pins are associated in triples.
        Each ID gets a light, a fan, and a mist nozzle.
        """
        # Compute bank based on ID number
        if self.ID == 1:
            self.bank = 0
            self.fan = 2
            self.light = 3
            self.valve = 4
        elif self.ID == 2:
            self.bank = 0
            self.fan = 5
            self.light = 6
            self.valve = 7
        elif self.ID = 3:
            self.bank = 1
            self.fan = 0
            self.light = 1
            self.valve = 2
        elif self.ID = 4:
            self.bank = 1
            self.fan = 3
            self.light = 5
            self.valve = 6
        else:
            raise Exception(
                "Mapping not available for ID: " + str(self.ID))

        # Check to make sure reserved pins are not requested
        if (self.bank == 0 and (min(self.fan, self.light, self.valve) == 0):
            raise Exception("Pin A0 is reserved for sensor modules")

        self.GPIO_dict=[{'ID': self.ID, 'bank': self.bank,
                      'fan': self.fan, 'valve': self.valve, 'light': self.light}]

        # Append dictionary to class and resort dictionary by ID # if needed
        ControlCluster.GPIOdict.append(self.GPIO_dict)
        ControlCluster.GPIOdict=sorted(
            ControlCluster.GPIOdict, key=itemgetter('ID'))

    def manage_lights(ID, ideal_per_day, current_total, current_sensor, ideal_sensor):
        if current_total < ideal_per_day:
            # The plant has not yet reached it's daily light budget
            if current_sensor <= ideal_sensor:
                # It is currently okay to turn on the light
                ControlCluster.bank_mask[
                    self.bank] += GPIO_add_to_mask(self.light, "high")
            else:
                ControlCluster.bank_mask[
                    self.bank] += GPIO_add_to_mask(self.light, "low")
        else:
            ControlCluster.bank_mask[
                    self.bank] += GPIO_add_to_mask(self.light, "low")
        return True

    def manage_fan(ID, operation):
        """ Usage:
                manageFans(1, "on") # Turn on the fan for plant 1
        """
        if operation == "on":
            ControlCluster.bank_mask[
                    self.bank] += GPIO_add_to_mask(self.fan, "high")
        else:
            ControlCluster.bank_mask[
                    self.bank] += GPIO_add_to_mask(self.light, "low")
        return True

    def manageValve(ID, ideal_moisture, current_moisture):
        """Manages turning on the mist pump based on water data from the plant.
        We will need to aggregate the total amount of water that the plant
        receives so that we can keep track of what it's receiving daily.

        This function will need to select a nozzle to open
        before turning on the mist pump.
        """
        if current_moisture < ideal_moisture:
            ControlCluster.bank_mask[
                    self.bank] += GPIO_add_to_mask(self.valve, "high")
            ControlCluster.pumpOperation[self.bank]=1
        else:
            ControlCluster.bank_mask[
                    self.bank] += GPIO_add_to_mask(self.light, "low")
            ControlCluster.pumpOperation[self.bank]=0
