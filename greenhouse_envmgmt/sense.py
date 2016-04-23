#!/usr/bin/python

# Contains class information for sensor nodes.
# Each plant is treated as a base, and each plant contains multiple sensors.
# Basic usage:
#   Create a plant record using:
#      plant1 = Plant(temp_addr, humidity_addr, lux_addr, adc_addr)
#   Updating individual sensor values can be done with
# Note that SMBus must be imported and initiated
#   in order to use these classes.
import smbus
from control import ControlCluster
from i2c_utility import get_ADC_value, import_i2c_addr
from i2c_utility import IO_expander_output, get_IO_reg
from time import sleep, time  # needed to force a delay in humidity module
from math import e


class IterList(type):
    """ Metaclass for iterating over sensor objects in a _list
    """
    def __iter__(cls):
        return iter(cls._list)


class SensorCluster(object):
    __metaclass__ = IterList
    _list = []
    water_remaining = 0

    def __init__(self, ID, address=None):
        sensor_addr = import_i2c_addr(SensorCluster.bus)
        if (ID < 1 or ID > len(sensor_addr)):
            raise I2CBusError("Plant ID out of range.")
        self.address = address or (sensor_addr[ID-1])
        self.ID = ID
        self.mux = TCAMux(self.address)
        self.humidity_temp = HIH71xx(0x27, 1)
        self.light = TSL255xx(0x39, 0)
        self.analog = MCP34xx(0x68, 2)
        self._list.append(self)


    @classmethod
    def update_all_sensors(cls, opt=None):
        """ Method iterates over all SensorCluster objects and updates 
            each sensor value and saves the values to the plant record.
                - Note that it must receive an open bus object.
            Usage: 
            Update all sensors exluding analog sensors that need power.
            - update_all_sensors()

            Update all sensors including soil moisture.
            - update_all_sensors("all")

        """
        for sensorobj in cls:
            sensorobj.update_instance_sensors(opt)

    def update_instance_sensors(self, opt=None):

        """ Method runs through all sensor modules and updates 
            to the latest sensor values.
        After running through each sensor module,
        The sensor head (the I2C multiplexer), is disabled
        in order to avoid address conflicts.
        Usage:
            plant_sensor_object.updateAllSensors(bus_object)
        """
        self.open(light)
        self.light.update()
        self.open(humidity_temp)
        self.humidity_temp.update()
        if opt == "all":
            try:
                self.open(analog)
                self.analog.update()
            except SensorError:
                # This could be handled with a repeat request later.
                pass
        # disable sensor module
        status = self.close()
        if status != 0:
            raise I2CBusError(
                "Bus multiplexer was unable to switch off to prevent conflicts")

    def sensor_values(self):
        """
        Returns the values of all sensors for this cluster
        """
        self.update_instance_sensors(opt="all")
        return {
            "light": self.light.lux,
            "water": self.analog.soil_moisture.,
            "humidity": self.humidity_temp.humidity,
            "temperature": self.humidity_temp.temp
        }


    def open(self, sensor):
        """ Opens a requested sensor to the bus"""
        self.mux.select(sensor.channel)

    def close(self):
        """ Closes all sensors in a cluster off from the bus"""
        self.mux.select("off")

    
    @classmethod
    def get_water_level(cls):
        """ This method uses the ADC on the control module to measure
            the current water tank level and returns the water volume
            remaining in the tank.

            For this method, it is assumed that a simple voltage divider
            is used to interface the sensor to the ADC module.
            
            Testing shows that the sensor response is not completely linear,
                though it is quite close. To make the results more accurate,
                a mapping method approximated by a linear fit to data is used.
        """
        # ----------
        # These values should be updated based on the real system parameters
        bus = smbus.SMBus(1)
        vref = 4.95
        tank_height = 17.5 # in centimeters (height of container)
        rref = 2668  # Reference resistor
        # ----------
        val = 0
        for i in range(5):
            # Take five readings and do an average
            # Fetch value from ADC (0x69 - ch1)
            val = get_ADC_value(bus, 0x6c, 1) + val
        avg = val / 5
        water_sensor_res = rref * avg/(vref - avg)
        depth_cm = water_sensor_res * \
                    (-.0163) + 28.127 # measured transfer adjusted offset
        if depth_cm < 1.0: # Below 1cm, the values should not be trusted.
            depth_cm = 0
        cls.water_remaining = depth_cm / tank_height
        # Return the current depth in case the user is interested in
        #   that parameter alone. (IE for automatic shut-off)
        return depth_cm/tank_height


class I2CSensor(object):
    """ Base class for I2C enabled sensors."""

    __metaclass__ = IterList
    _list = []
    bus = None

    def __init__(self, address, channel):
        """ Initializes an I2CSensor object. 
        Must receive an I2C address in hex or decimal. 
        Must receive a metric type as a string.
        """
        # Open a bus if one isn't active already
        if I2CSensor.bus is None:
            I2CSensor.bus = smbus.SMBus(1)

        self.address = address
        self.channel = channel # Sensors start with a value of 0
        self._list.append(self) # Track a list of all I2CSensor devices

    def update(self):
        pass

    def measures(self):
        return self.metric

    def set_address(self, addr):
        self.address = addr



class HIH71xx(I2CSensor):
    metric = ['humidity', 'temperature']

    def __init__(self, address, channel):
        I2CSensor.__init__(self,address, channel)
        self._humidity = 0
        self._temp = 0


    def update(self):
        STATUS = 0b11 << 6
        self.bus.write_quick(self.address)  # Begin conversion
        sleep(.25)
        # wait 100ms to make sure the conversion takes place.
        data = self.bus.read_i2c_block_data(SensorCluster.humidity_addr, 0, 4)
        status = (data[0] & STATUS) >> 6
        if status == 0 or status == 1:  # will always pass for now.
            humidity = round((((data[0] & 0x3f) << 8) |
                              data[1]) * 100.0 / (2**14 - 2), 3)
            self.humidity = humidity
            self.temp = (round((((data[2] << 6) + ((data[3] & 0xfc) >> 2))
                               * 165.0 / 16382.0 - 40.0), 3) * 9/5) + 32
        else:
            raise I2CBusError("Unable to retrieve humidity")


    def humidity():
        doc = "Humidity property"
        def fget(self):
            return self._humidity
        def fset(self, value):
            self._humidity = value
        return locals()
    humidity = property(**humidity())

    def temp():
        doc = "Temperature property"
        def fget(self):
            return self._temp
        def fset(self, value):
            self._temp = value
        return locals()
    light = property(**temp())


class TSL255xx(I2CSensor):
    """ Class to handle exchanges between a caller
        and a TSL255 Ambient Light Sensor.

        Attributes:
        obj.lux
        obj.light_ratio
    """
    metric = ['light']


    def __init__(self, address, channel):
        I2CSensor.__init__(self,address, channel)
        self._lux = 0
        self._light_ratio = 0

    def update(self, extend=1):
        """ Communicates with the TSL2550D light sensor and returns a 
            lux value. 
        Note that this method contains some degree of delay. 
        Alternatively, the device could be put in extended mode, 
            which drops some resolution in favor of shorter delays.

        Default operation is extended mode.
        """
        DEVICE_REG_OUT = 0x1d
        LUX_PWR_ON = 0x03
        if extend == 1:
            LUX_MODE = 0x1d
            delay = .08
            scale = 5
        else:
            LUX_MODE = 0x18
            delay = .4
            scale = 1
        LUX_READ_CH0 = 0x43
        LUX_READ_CH1 = 0x83
        # Make sure lux sensor is powered up.
        self.bus.write_byte(self.address, LUX_PWR_ON)
        lux_on = self.bus.read_byte_data(self.address, LUX_PWR_ON)
        # Check for successful powerup
        if (lux_on == LUX_PWR_ON):
            # Send command to initiate ADC on each channel
            # Read each channel after the new data is ready
            self.bus.write_byte(self.address, LUX_MODE)
            self.bus.write_byte(self.address, LUX_READ_CH0)
            sleep(delay)
            adc_ch0 = self.bus.read_byte(self.address)
            count0 = get_lux_count(adc_ch0) * scale  # 5x for extended mode
            self.bus.write_byte(self.address, LUX_READ_CH1)
            sleep(delay)
            adc_ch1 = self.bus.read_byte(self.address)
            count1 = get_lux_count(adc_ch1) * scale  # 5x for extended mode
            ratio = count1 / (count0 - count1)
            lux = (count0 - count1) * .39 * e**(-.181 * (ratio**2))
            self.light_ratio = float(count1)/float(count0)
            self.lux = round(lux, 3)
        else:
            raise SensorError("The lux sensor is powered down.")


    @staticmethod
    def get_lux_count(lux_byte):
        """ Method to convert data from the TSL2550D lux sensor
        into more easily usable ADC count values.

        """
        LUX_VALID_MASK = 0b10000000
        LUX_CHORD_MASK = 0b01110000
        LUX_STEP_MASK = 0b00001111
        valid = lux_byte & LUX_VALID_MASK
        if valid != 0:
            step_num = (lux_byte & LUX_STEP_MASK)
            # Shift to normalize value
            chord_num = (lux_byte & LUX_CHORD_MASK) >> 4
            step_val = 2**chord_num
            chord_val = int(16.5 * (step_val - 1))
            count = chord_val + step_val * step_num
            return count
        else:
            raise SensorError("Invalid lux sensor data.")

    def lux():
        doc = "Lux property"
        def fget(self):
            return self._lux
        def fset(self, value):
            self._lux = value
        return locals()
    lux = property(**lux())

    def light_ratio():
        doc = "Lux property"
        def fget(self):
            return self._light_ratio
        def fset(self, value):
            self._light_ratio = value
        return locals()
    light_ratio = property(**light_ratio())

class MCP34xx(I2CSensor):
    metric = ['analog']
    analog_power_pin = 0 # See ControlCluster class to ensure no conflicts
    power_bank = 0  # bank and pin used to toggle analog sensor power
    soil_chan = 1

    def __init__(self, address, channel):
        I2CSensor.__init__(self,address, channel)
        self._soil_moisture = 0


    def update(self, channel=MCP34xx.soil_chan):
        """ Method will select the ADC module,
                turn on the analog sensor, wait for voltage settle, 
                and then digitize the sensor voltage. 
            Voltage division/signal loss is accounted for by 
                scaling up the sensor output.
                This may need to be adjusted if a different sensor is used
        """

        MCP34xx.analog_sensor_power(self.bus, "on")

        sleep(.2)
        moisture = get_ADC_value(
            self.bus, self.address, MCP34xx.soil_chan)

        analog_sensor_power(self.bus, "off")  # turn off sensor

        if (moisture >= 0):
            soil_moisture = moisture/2.048 # Scale to a percentage value 
            self.soil_moisture = round(soil_moisture,3)
        else:
            raise SensorError(
                "The soil moisture meter is not configured correctly.")
        return status

    @staticmethod
        """ Method to toggle power to the analog sensors attached to the ADC. 
        If power to these sensors is always-on, this method need not be used.

        operation="on" or "off"
        """
        def analog_sensor_power(bus, operation):
            """ Method that turns on all of the analog sensor modules
                Includes all attached soil moisture sensors
                Note that all of the SensorCluster object should be attached
                    in parallel and only 1 GPIO pin is available
                    to toggle analog sensor power.
                The sensor power should be left on for at least 100ms
                    in order to allow the sensors to stabilize before reading. 
                    Usage:  SensorCluster.analog_sensor_power(bus,"high")
                    OR      SensorCluster.analog_sensor_power(bus,"low")
                This method should be removed if an off-board GPIO extender is used.
            """
            # Set appropriate analog sensor power bit in GPIO mask
            # using the ControlCluster bank_mask to avoid overwriting any data
            reg_data = get_IO_reg(bus, 0x20, cls.power_bank)

            if operation == "on":
                reg_data = reg_data | 1 << cls.analog_power_pin
            elif operation == "off":
                reg_data = reg_data & (0b11111111 ^ (1 << cls.analog_power_pin))
            else:
                raise SensorError(
                    "Invalid command used while enabling analog sensors")
            # Send updated IO mask to output
            IO_expander_output(bus, 0x20, cls.power_bank, reg_data)

    def soil_moisture():
        doc = "Soil Moisture property"
        def fget(self):
            return self._soil_moisture
        def fset(self, value):
            self._soil_moisture = value
        return locals()
    soil_moisture = property(**soil_moisture())


class TCAMux(I2CSensor):

    def __init__(self, address):
        I2CSensor.__init__(self,address, channel=None)
        

    def select(self, channel):
    """
        This function will write to the control register of the
                TCA module to select the channel that will be
                exposed on the TCA module.
        After doing this, the desired module can be used as it would be normally.
                (The caller should use the address of the I2C sensor module.
        The TCA module is only written to when the channel is switched.)
                addr contains address of the TCA module
                channel specifies the desired channel on the TCA that will be used.

        Usage - Enable a channel
            select(bus, self.mux_addr, channel_to_enable)
                Channel to enable begins at 0 (enables first channel)
                                    ends at 3 (enables fourth channel)

        Usage - Disable all channels
            select(bus, self.mux_addr, "off")
                This call must be made whenever the sensor node is no longer
                    being accessed.
                If this is not done, there will be addressing conflicts.
    """
    if addr < 0x70 or self.address > 0x77:
        print("The TCA address(" + str(addr) + ") is invalid. Aborting")
        return False
    if channel == "off":
        self.bus.write_byte(self.address, 0)
    elif channel < 0 or channel > 3:
        print("The requested channel does not exist.")
        return False
    else:
        self.write_byte(self.address, 1 << channel)

    status = bus.read_byte(addr)
    return status

class SensorError(Exception):
    """ Non-fatal
        Implies that a sensor is either turned off
            or unplugged from its slot. 
        All I2C objects within the sensor cluster should 
            be turned off before doing anything else.
    """
    pass


class I2CBusError(Exception):
    """ Typically fatal 
        - Something on the bus has become unresponsive.
        - Should occur if the I2C multiplexer is not disabled
            after successive updates. 
    """
    pass


