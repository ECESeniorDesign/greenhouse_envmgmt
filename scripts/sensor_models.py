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
from i2c_utility import TCA_select, get_ADC_value, IO_expander_output
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

    def update_lux(self, bus):
        # This will currently only work with one lux sensor, as the
        # i2c multiplexer still needs to be implemented.
        DEVICE_REG_OUT = 0x1d
        LUX_PWR_ON = 0x03
        LUX_PWR_OFF = 0x00
        LUX_READ_CH0 = 0x43
        LUX_READ_CH1 = 0x83
        LUX_VALID_MASK = 0b10000000
        LUX_CHORD_MASK = 0b01110000
        LUX_STEP_MASK = 0b00001111

        # Select correct I2C mux channel on TCA module
        TCA_select(bus, self.mux_addr, SensorCluster.lux_chan)
        # Make sure lux sensor is powered up.
        bus.write_byte(SensorCluster.lux_addr, LUX_PWR_ON)
        lux_on = bus.read_byte_data(SensorCluster.lux_addr, LUX_PWR_ON)

        # Check for successful powerup
        if (lux_on == LUX_PWR_ON):
            # Send command to initiate ADC on each channel
            # Read each channel after the new data is ready
            bus.write_byte(SensorCluster.lux_addr, LUX_READ_CH0)
            adc_ch0 = bus.read_byte_data(SensorCluster.lux_addr, LUX_READ_CH0)
            # Calculate ch0 metrics
            ch0_valid = adc_ch0 & LUX_VALID_MASK
            if (ch0_valid == 0):
                raise SensorError("The lux sensor has returned invalid data")
            else:
                ch0_step_num = (adc_ch0 & LUX_STEP_MASK)
                # Shift to normalize value
                ch0_chord = (adc_ch0 & LUX_CHORD_MASK) >> 4
                ch0_step_val = int(16.5 * ((2**ch0_step_num) - 1))
                ch0_count_val = ch0_chord + (ch0_step_val * ch0_step_num)
                # print "adc_ch0 = " + str(adc_ch0)
                # print "adc_ch1 counts = " + str(ch0_count_val)
                # Calculate ch1 metrics
                bus.write_byte(SensorCluster.lux_addr, LUX_READ_CH1)
                adc_ch1 = bus.read_byte_data(
                    SensorCluster.lux_addr, LUX_READ_CH1)
                ch1_valid = adc_ch1 & LUX_VALID_MASK
                # print "adc_ch1 = " + str(adc_ch1)
            if (ch1_valid == 0):
                raise SensorError("The lux sensor has returned invalid data")
            else:
                ch1_step_num = (adc_ch1 & LUX_STEP_MASK)
                ch1_chord = (adc_ch1 & LUX_CHORD_MASK) >> 4
                ch1_step_val = int(16.5 * ((2**ch1_step_num) - 1))
                ch1_count_val = ch1_chord + (ch1_step_val * ch1_step_num)
                # calculate lux value
                R = ch1_count_val / (ch0_count_val - ch1_count_val)
                lux_level = ((adc_ch0 & ~LUX_VALID_MASK) -
                             (adc_ch1 & ~LUX_VALID_MASK)) \
                    * .39 * e**(-.181 * (R**2))
                self.lux = round(lux_level, 3)
                return TCA_select(bus, self.mux_addr, "off")
        else:
            raise SensorError("The lux sensor is powered down.")

    def update_humidity_temp(self, bus):
        """ This method utilizes the HIH7xxx sensor to read
            humidity and temperature in one call. 
        """
        # Create mask for STATUS (first two bits of 64 bit wide result)
        STATUS = 0b11 << 6
        TCA_select(bus, self.mux_addr, SensorCluster.humidity_chan)
        bus.write_quick(SensorCluster.humidity_addr)  # Begin conversion
        for i in range(3):
            sleep(.25)
            # wait 100ms to make sure the conversion takes place.
            data = bus.read_i2c_block_data(SensorCluster.humidity_addr, 0, 4)
            status = (data[0] & STATUS) >> 6
            if status == 0 or status == 1:  # will always pass for now.
                humidity = round((((data[0] & 0x3f) << 8) |
                                  data[1]) * 100.0 / (2**14 - 2), 3)
                self.humidity = humidity
                self.temp = round((((data[2] << 6) + ((data[3] & 0xfc) >> 2))
                                   * 165.0 / 16382.0 - 40.0), 3)
                return TCA_select(bus, self.mux_addr, "off")
        raise I2CBusError("Unable to retrieve humidity")

    def update_soil_moisture(self, bus):
        """ Method will select the ADC module,
                turn on the analog sensor, wait for voltage settle, 
                and then digitize the sensor voltage. 
            Voltage division/signal loss is accounted for by 
                scaling up the sensor output.
                This may need to be adjusted if a different sensor is used
        """
        SensorCluster.analog_sensor_power(bus,"on") # turn on sensor
        sleep(.5)
        TCA_select(bus, self.mux_addr, SensorCluster.adc_chan)
        moisture = get_ADC_value(
            bus, SensorCluster.adc_addr, SensorCluster.moisture_chan)
        moisture *= 2  # Account for voltage division within moisture sensor
        status = TCA_select(bus, self.mux_addr, "off")  # Turn off mux.
        SensorCluster.analog_sensor_power(bus,"off") # turn off sensor
        if (moisture > 0.1 and moisture < .985):
            self.soil_moisture = round(moisture, 3)
        else:
            raise SensorError(
                "The soil moisture meter is either unplugged or powered off.")
        return status

    def update_instance_sensors(self, bus):
        """ Method runs through all sensor modules and updates 
            to the latest sensor values.
        After running through each sensor module,
        The sensor head (the I2C multiplexer), is disabled
        in order to avoid address conflicts.
        Usage:
            plant_sensor_object.updateAllSensors(bus_object)
        """

        self.update_lux(bus)
        self.update_humidity_temp(bus)
        try:
            self.update_soil_moisture(bus)
        except SensorError:
            # This could be handled with a repeat request later.
            pass
        self.timestamp = time()
        # disable sensor module
        tca_status = TCA_select(bus, self.mux_addr, "off")
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
    def update_all_sensors(cls, bus):
        """ Method iterates over all SensorCluster objects and updates 
            each sensor value and saves the values to the plant record.
                - Note that it must receive an open bus object.
            Usage: updateAllSensors(bus)
        """
        for sensorobj in cls:
            sensorobj.update_instance_sensors(bus)
            sensorobj.save_instance_sensors()

    @classmethod
    def analog_sensor_power(cls, bus, string):
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
        if string == "on":
            ControlCluster.bank_mask[cls.power_bank] = ControlCluster.bank_mask[cls.power_bank] | \
                1 << cls.analog_power_pin
        elif string == "off":
            ControlCluster.bank_mask[cls.power_bank] = ControlCluster.bank_mask[cls.power_bank] & \
                (0b11111111 ^ (1 << cls.analog_power_pin))
        else:
            raise SensorError(
                "Invalid command used while enabling analog sensors")
        # Send updated IO mask to output
        IO_expander_output(bus, 0x20, cls.power_bank,
                           ControlCluster.bank_mask[cls.power_bank])


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
