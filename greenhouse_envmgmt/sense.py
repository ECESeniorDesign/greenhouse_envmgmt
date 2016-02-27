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
import app.models as models
from app.config import DATABASE
from controls import ControlCluster
from i2c_utility import TCA_select, get_ADC_value, IO_expander_output, get_IO_reg
from time import sleep, time  # needed to force a delay in humidity module
from math import e


class IterList(type):
    """ Metaclass for iterating over sensor objects in a _list
    """
    def __iter__(cls):
        return iter(cls._list)


class SensorCluster(object):
    'Base class for each individual plant containing sensor info'
    __metaclass__ = IterList
    _list = []
    analog_power_pin = 2
    power_bank = 0  # bank and pin used to toggle analog sensor power
    temp_addr = 0x48
    temp_chan = 3
    humidity_addr = 0x27
    humidity_chan = 1
    lux_addr = 0x39
    lux_chan = 0
    adc_addr = 0x68
    adc_chan = 2
    moisture_chan = 1
    tank_adc_adr = 0x69
    tank_adc_chan = 0
    bus = None

    def __init__(self, ID, mux_addr):

        # Initializes cluster, enumeration, and sets up address info
        if (ID < 1):
            raise Exception("Plant IDs must start at 1")
        self.ID = ID  # Plant number specified by caller
        self.mux_addr = mux_addr
        self.temp = 0
        self.humidity = 0
        self.lux = 0
        self.soil_moisture = 0
        self.acidity = 0
        self.timestamp = time()  # record time at instantiation
        self._list.append(self)
        self.update_count = 0

    def update_lux(self, extend=0):
        """ Communicates with the TSL2550D light sensor and returns a 
            lux value. 

        Note that this method contains approximately 1 second of total delay.
            This delay is necessary in order to obtain full resolution
            compensated lux values.

        Alternatively, the device could be put in extended mode, 
            which drops some resolution in favor of shorter delays.

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
        # Select correct I2C mux channel on TCA module

        TCA_select(SensorCluster.bus, self.mux_addr, SensorCluster.lux_chan)
        # Make sure lux sensor is powered up.
        SensorCluster.bus.write_byte(SensorCluster.lux_addr, LUX_PWR_ON)
        lux_on = SensorCluster.bus.read_byte_data(SensorCluster.lux_addr, LUX_PWR_ON)
        
        # Check for successful powerup
        if (lux_on == LUX_PWR_ON):
            # Send command to initiate ADC on each channel
            # Read each channel after the new data is ready
            SensorCluster.bus.write_byte(SensorCluster.lux_addr, LUX_MODE)
            SensorCluster.bus.write_byte(SensorCluster.lux_addr, LUX_READ_CH0)
            sleep(delay)
            adc_ch0 = SensorCluster.bus.read_byte(SensorCluster.lux_addr)
            count0 = get_lux_count(adc_ch0) * scale  # 5x for extended mode
            SensorCluster.bus.write_byte(SensorCluster.lux_addr, LUX_READ_CH1)
            sleep(delay)
            adc_ch1 = SensorCluster.bus.read_byte(SensorCluster.lux_addr)
            count1 = get_lux_count(adc_ch1) * scale  # 5x for extended mode
            ratio = count1 / (count0 - count1)
            lux = (count0 - count1) * .39 * e**(-.181 * (ratio**2))
            self.lux = round(lux, 3)
            return TCA_select(SensorCluster.bus, self.mux_addr, "off")
        else:
            raise SensorError("The lux sensor is powered down.")

    def update_humidity_temp(self):
        """ This method utilizes the HIH7xxx sensor to read
            humidity and temperature in one call. 
        """
        # Create mask for STATUS (first two bits of 64 bit wide result)
        STATUS = 0b11 << 6

        TCA_select(SensorCluster.bus, self.mux_addr, SensorCluster.humidity_chan)
        SensorCluster.bus.write_quick(SensorCluster.humidity_addr)  # Begin conversion
        sleep(.25)
        # wait 100ms to make sure the conversion takes place.
        data = SensorCluster.bus.read_i2c_block_data(SensorCluster.humidity_addr, 0, 4)
        status = (data[0] & STATUS) >> 6
        
        if status == 0 or status == 1:  # will always pass for now.
            humidity = round((((data[0] & 0x3f) << 8) |
                              data[1]) * 100.0 / (2**14 - 2), 3)
            self.humidity = humidity
            self.temp = round((((data[2] << 6) + ((data[3] & 0xfc) >> 2))
                               * 165.0 / 16382.0 - 40.0), 3)
            return TCA_select(SensorCluster.bus, self.mux_addr, "off")
        else:
            raise I2CBusError("Unable to retrieve humidity")

    def update_soil_moisture(self):
        """ Method will select the ADC module,
                turn on the analog sensor, wait for voltage settle, 
                and then digitize the sensor voltage. 
            Voltage division/signal loss is accounted for by 
                scaling up the sensor output.
                This may need to be adjusted if a different sensor is used
        """
        SensorCluster.analog_sensor_power(SensorCluster.bus, "on")  # turn on sensor
        sleep(.2)
        TCA_select(SensorCluster.bus, self.mux_addr, SensorCluster.adc_chan)
        moisture = get_ADC_value(
            SensorCluster.bus, SensorCluster.adc_addr, SensorCluster.moisture_chan)
        status = TCA_select(SensorCluster.bus, self.mux_addr, "off")  # Turn off mux.
        SensorCluster.analog_sensor_power(SensorCluster.bus, "off")  # turn off sensor
        if (moisture > 0.1 and moisture < .985):
            self.soil_moisture = round(moisture, 3)
        else:
            raise SensorError(
                "The soil moisture meter is either unplugged or powered off.")
        return status

    def update_instance_sensors(self, opt=None):

        """ Method runs through all sensor modules and updates 
            to the latest sensor values.
        After running through each sensor module,
        The sensor head (the I2C multiplexer), is disabled
        in order to avoid address conflicts.
        Usage:
            plant_sensor_object.updateAllSensors(bus_object)
        """
        self.update_count += 1
        self.update_lux()
        self.update_humidity_temp()
        if opt == "all":
            try:
                self.update_soil_moisture()
            except SensorError:
                # This could be handled with a repeat request later.
                pass
        self.timestamp = time()
        # disable sensor module

        tca_status = TCA_select(SensorCluster.bus, self.mux_addr, "off")
        if tca_status != 0:
            raise I2CBusError(
                "Bus multiplexer was unable to switch off to prevent conflicts")

    def save_instance_sensors(self):
        # Saves all of the current sensor values
        # to the webservice Plant object
        plant = models.Plant.for_slot(self.ID, raise_if_not_found=False)
        if plant:
            plant.record_sensor(sensor_name="light", sensor_value=self.lux)
            plant.record_sensor(sensor_name="water",
                                sensor_value=self.soil_moisture)
            plant.record_sensor(sensor_name="humidity",
                                sensor_value=self.humidity)
            plant.record_sensor(sensor_name="temperature",
                                sensor_value=self.temp)
        else:
            raise SensorError("Could not save sensor values.")

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
            sensorobj.save_instance_sensors()

    @classmethod
    def analog_sensor_power(cls, bus, operation):
        """ Method that turns on all of the analog sensor modules
            Includes all attached soil moisture sensors
            Note that all of the SensorCluster object should be attached
                in parallel and only 1 GPIO pin is available
                to toggle analog sensor power.
            The sensor power should be left on for at least 100ms
                in order to allow the sensors to stabilize before reading. 
<<<<<<< HEAD
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

    @classmethod
    def get_water_level(cls):
        """ This method uses the ADC on the control module to measure
            the current water tank level and returns the water volume
            remaining in the tank.

            For this method, it is assumed that a simple voltage divider
            is used to interface the sensor to the ADC module.
            
        """
        # ----------
        # These values should be updated based on the real system parameters
        tank_height = 10
        vref = 5  # voltage reference
        rref = 560  # Reference resistor (or pot)
        # ----------
        for i in range(5):
            # Take five readings and do an average
            # Fetch value from ADC (0x69 - ch1)
            val = get_ADC_value(cls.bus, 0x6c, 1) + val
        water_sensor_avg = val / 5
        water_sensor_resistance = rref / (water_sensor_avg - 1)
        exposed_cm = water_sensor_resistance / 56  # sensor is ~56 ohms/cm
        depth_cm = 21.3 - exposed_cm # calculate submerged length
        cls.water_remaining = depth_cm / tank_height
        # Return the current depth in case the user is interested in
        #   that parameter alone. (IE for automatic shut-off)
        return depth_cm


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
