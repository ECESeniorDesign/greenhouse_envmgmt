#!/usr/bin/python
from i2c_utility import IO_expander_output, get_ADC_value
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

            Turning on control units individually:
                plant1Control.manage("fan", "on")
                plant1Control.manage("light", "off")
                plant1Control.update(bus)

    """
    GPIOdict = []
    pump_pin = 0  # Pin A0 is assigned to the
    pump_bank = 0
    current_volume = 0

    @classmethod
    def get_water_level(cls, bus):
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
        cls.water_remaining = depth_cm / tank_height
        # Return the current depth in case the user is interested in
        #   that parameter alone. (IE for automatic shut-off)
        return depth_cm

    def update(self, bus):
        """ This method exposes a more simple interface to the IO module
        Regardless of what the control instance contains, this method
        will transmit the queued IO commands to the IO expander

        Usage: plant1Control.update(bus)
        """
        IO_expander_output(
            bus, self.IOexpander,
            self.bank,
            self.mask)

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
            raise InvalidIOMap(
                "Mapping not available for ID: " + str(self.ID))

        # Check to make sure reserved pins are not requested
        if (self.bank == 0) and (min(self.fan, self.light, self.valve) < 2):
            raise InvalidIOMap(
                "Pins A0 and A1 are reserved for other functions")

        self.GPIO_dict = [{'ID': self.ID, 'bank': self.bank,
                           'fan': self.fan, 'valve': self.valve, 'light': self.light}]

        # Append dictionary to class and resort dictionary by ID # if needed
        ControlCluster.GPIOdict.append(self.GPIO_dict)
        # ControlCluster.GPIOdict=sorted(
        #    ControlCluster.GPIOdict, key=itemgetter('ID'))

    def manage_light(self, operation):
        """ Turns on the lights depending on the operation command
        Usage:
            manage_lights("on")
        """
        return self.manage("light", operation)

    def manage_fan(self, operation):
        """ Usage:
                manageFans("on") # Turn on the fan for plant 1
        """
        return self.manage("fan", operation)

    def manage_valve(self, operation):
        """Manages turning on the mist pump based on water data from the plant.
        We will need to aggregate the total amount of water that the plant
        receives so that we can keep track of what it's receiving daily.

        This function will need to select a nozzle to open
        before turning on the mist pump.
        """
        return self.manage("valve", operation)

    def manage_pump(self, operation):
        """
        Updates control module knowledge of pump requests.
        If any sensor module requests water, the pump will turn on.
        Note that if this desire is not desired, one should verify
            that all plants have set the pump_operation bit to 1.

        """
        if operation == "on":
            ControlCluster.pump_operation[self.ID - 1] = 1
        elif operation == "off":
            ControlCluster.pump_operation[self.ID - 1] = 0
        if 1 in ControlCluster.pump_operation:
            # Turn the pump on
            self.controls["pump"] = "on"
        else:
            # Turn the pump off
            self.controls["pump"] = "off"
        return True

    def manage(self, control, operation):
        if control not in {"light", "valve", "fan", "pump"}:
            raise IOExpanderFailure(
                "Invalid controller")
        if operation not in ["on", "off"]:
            raise IOExpanderFailure(
                "Invalid operation passed to {} controller".format(control))
        if control == "pump":
            return self.manage_pump(operation)
        else:
            self.controls[control] = operation
            return True

    def control(self, bus, on=[], off=[]):
        """
        This method serves as the primary interaction point
            to the controls interface.
        - The user must pass an SMBus object. 
        - The 'on' and 'off' arguments can either be a list or a single string.
            This allows for both individual device control and batch controls.

        Note:
            Both the onlist and offlist are optional. 
            If only one item is being managed, it can be passed as a string.

        Usage:
            - Turning off all devices:
                ctrlobj.control(bus, off="all")
            - Turning on all devices:
                ctrlobj.control(bus, on="all")

            - Turning on the light and fan ONLY (for example)
                ctrlobj.control(bus, on=["light", "fan"])

            - Turning on the light and turning off the fan (for example)
                ctrolobj.control(bus, on="light", off="fan")

        """
        controls = {"light", "valve", "fan", "pump"}
        def cast_arg(arg):
            if type(arg) is str:
                if arg == "all":
                    return controls
                else:
                    return {arg} & controls
            else:
                return set(arg) & controls

        # User has requested individual controls.
        for item in cast_arg(on):
            self.manage(item, "on")
        for item in cast_arg(off):
            self.manage(item, "off")
        return self.update(bus)

    @property
    def mask(self):

        def construct_mask(mask, control):
            if self.controls[control] == "on":
                return mask | 1 << self.GPIO_dict[0][control]
            else:
                return mask

        # probably should hold a constant of these somewhere
        controls = ["fan", "light", "valve"]

        mask = reduce(construct_mask, controls, 0x0)

        # handle pump separately
        if self.bank == 0 and self.controls["pump"] == "on":
            mask |= 1 << ControlCluster.pump_pin

        return mask

    def __init__(self, ID):
        self.ID = ID
        self.form_GPIO_map()
        self.controls = {"light": "off", "valve": "off", "fan": "off", "pump": "off"}
        # Create dynamically sized lists to hold IO data
        ControlCluster.pump_operation = [0] * len(ControlCluster.GPIOdict)
        ControlCluster.bank_mask = [0] * len(ControlCluster.GPIOdict)


class IOExpanderFailure(Exception):
    pass


class InvalidIOMap(Exception):
    pass
