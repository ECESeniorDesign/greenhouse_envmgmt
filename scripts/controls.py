#!/usr/bin/python
from i2c_utility import GPIO_update_output, get_ADC_value
from operator import itemgetter
from math import pi


class ControlCluster(object):
    """ This class serves as a control module for each plant's
            fan, light, and pump valve.

        Upon instantiation, the class will use it's ID in order to
            generate a GPIO mapping corresponding to the pins on the MCP
            IO expander.

        Currently, only four plant control sets can be supported. IDs
            must be greater than 1 and no higher than 4.

        Usage: plant1Control = ControlCluster(1)
            This will create the first plant control unit.

    """
    GPIOdict = []
    pumpPin = 0  # Pin A0 is assigned to the
    pumpBank = 0
    current_volume = 0

    @classmethod
    def get_tank_volume(cls, bus):
        """ This method uses the ADC on the control module to measure
            the current water tank level and returns the water volume
            remaining in the tank.
        """
        # ----------
        # These values should be updated based on the real system parameters
        tank_height = 10
        vref = 5  # voltage reference
        rref = 10000  # Reference resistor (or pot)
        # ----------
        for i in range(5):
            # Take five readings and do an average
            # Fetch value from ADC (0x69 - ch1)
            val = get_ADC_value(bus, 0x69, 1) + val
        water_sensor_avg = val / 5
        water_sensor_resistance = rref / (water_sensor_avg - 1)
        depth_cm = water_sensor_resistance / 59  # sensor is ~59 ohms/cm
        cls.water_remaining = depth_cm/tank_height
        # Return the current depth in case the user is interested in
        #   that parameter alone. (IE for automatic shut-off)
        return depth_cm

    def form_GPIO_map(self):
        """ This method creates a dictionary to map plant IDs to
        GPIO pins are associated in triples.
        Each ID gets a light, a fan, and a mist nozzle.
        """
        # Compute bank/pins/IOexpander address based on ID
        if self.ID == 1:
            self.IOexpander = 0x20
            self.bank = 0
            self.fan = 2
            self.light = 3
            self.valve = 4
        elif self.ID == 2:
            self.IOexpander = 0x20
            self.bank = 0
            self.fan = 5
            self.light = 6
            self.valve = 7
        elif self.ID == 3:
            self.IOexpander = 0x20
            self.bank = 1
            self.fan = 0
            self.light = 1
            self.valve = 2
        elif self.ID == 4:
            self.IOexpander = 0x20
            self.bank = 1
            self.fan = 3
            self.light = 5
            self.valve = 6
        else:
            raise Exception(
                "Mapping not available for ID: " + str(self.ID))

        # Check to make sure reserved pins are not requested
        if (self.bank == 0) and (min(self.fan, self.light, self.valve) < 2):
            raise Exception("Pins A0 and A1 are reserved for other functions")

        self.GPIO_dict = [{'ID': self.ID, 'bank': self.bank,
                           'fan': self.fan, 'valve': self.valve, 'light': self.light}]

        # Append dictionary to class and resort dictionary by ID # if needed
        ControlCluster.GPIOdict.append(self.GPIO_dict)
        # ControlCluster.GPIOdict=sorted(
        #    ControlCluster.GPIOdict, key=itemgetter('ID'))

    def manage_lights(self, operation):
        """ Turns on the lights depending on the operation command
        Usage:
            manage_lights("on")
        """

        if operation == "on":
            # It is currently okay to turn on the light
            ControlCluster.bank_mask[
                self.bank] = (1 << self.light) | (ControlCluster.bank_mask[self.bank])
        elif operation == "off":
            ControlCluster.bank_mask[
                self.bank] = ~(1 << self.light) & (ControlCluster.bank_mask[self.bank])
        else:
            raise Exception("Invalid operation passed to light controller")
        return True

    def manage_fan(self, operation):
        """ Usage:
                manageFans("on") # Turn on the fan for plant 1
        """
        if operation == "on":
            ControlCluster.bank_mask[
                self.bank] = (1 << self.fan) | (ControlCluster.bank_mask[self.bank])
        elif operation == "off":
            ControlCluster.bank_mask[
                self.bank] = ~(1 << self.fan) & (ControlCluster.bank_mask[self.bank])
        else:
            raise Exception("Invalid operation passed to fan controller")
        return True

    def manage_valve(self, operation):
        """Manages turning on the mist pump based on water data from the plant.
        We will need to aggregate the total amount of water that the plant
        receives so that we can keep track of what it's receiving daily.

        This function will need to select a nozzle to open
        before turning on the mist pump.
        """
        if operation == "on":
            ControlCluster.bank_mask[
                self.bank] = (1 << self.valve) | (ControlCluster.bank_mask[self.bank])
        elif operation == "off":
            ControlCluster.bank_mask[
                self.bank] = ~(1 << self.valve) & (ControlCluster.bank_mask[self.bank])
        else:
            raise Exception("Invalid operation passed to valve controller")
        return True

    def __init__(self, ID):
        self.ID = ID
        self.form_GPIO_map()
        # Create dynamically sized cluster data lists
        ControlCluster.pumpOperation = [0] * len(ControlCluster.GPIOdict)
        ControlCluster.bank_mask = [0] * len(ControlCluster.GPIOdict)
