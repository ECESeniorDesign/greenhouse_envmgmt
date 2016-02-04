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
import models
from controls import ControlCluster
from i2c_utility import TCA_select, get_ADC_value
from time import sleep, time  # needed to force a delay in humidity module
from math import e


class SensorCluster(object):
    'Base class for each individual plant containing sensor info'
    ClusterCount = 0
    anlog_power_pin = 1
    GPIO_bank = 0  # bank and pin used to toggle analog sensor power
    temp_addr = 0x48
    temp_chan = 3
    humidity_addr = 0x27
    humidity_chan = 1
    lux_addr = 0x39
    lux_chan = 0
    adc_addr = 0x68
    adc_chan = 2
    moisture_chan = 1

    @classmethod
    def analogSensorPower(cls, bus, string):
        """ Method that turns on all of the analog sensor modules
            Includes all attached soil moisture sensors
            Note that all of the SensorCluster object should be attached
                in parallel and only 1 GPIO pin is available
                to toggle analog sensor power.
            The sensor power should be left on for at least 100ms
                in order to allow the sensors to stabilize before reading. 


                Usage:  SensorCluster.analogSensorPower("high")
                OR      SensorCluster.analogSensorPower("low")

            This method should be removed if an off-board GPIO extender is used.
        """
        # Set appropriate analog sensor power bit in GPIO mask
        # using the ControlCluster bank_mask to avoid overwriting any data
        if string == "on":
            ControlCluster.bank_mask[cls.GPIO_bank] = ControlCluster.bank_mask[cls.GPIO_bank] |
                1 << analog_power_pin
        elif string == "off":
            ControlCluster.bank_mask[cls.GPIO_bank] = ControlCluster.bank_mask[cls.GPIO_bank] &
                (0b11111111 ^ (1 << analog_power_pin))
        else:
            print("Invalid command")
            return False
        # Send updated IO mask to output
        GPIO_update_output(bus, 0x20, cls.GPIO_bank,
                           ControlCluster.bank_mask[cls.GPIO_bank])
        return True

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
        SensorCluster.ClusterCount += 1

    def updateTemp(self, bus):
        # Method will update the temp attribute and return the value to the
        # caller
        DEVICE_TEMP_CMD = 0x00  # Command to read temperature
        TCA_select(bus, self.mux_addr, SensorCluster.temp_chan)
        self.temp = bus.read_byte_data(self.temp_addr, DEVICE_TEMP_CMD)
        # print "Current temperature for Plant " + str(self.num) + "is " +
        # str(temp)
        return True

    def updateLux(self, bus):
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
            print("Reading lux sensor data")
            bus.write_byte(SensorCluster.lux_addr, LUX_READ_CH0)
            print("....")
            adc_ch0 = bus.read_byte_data(SensorCluster.lux_addr, LUX_READ_CH0)
            # Calculate ch0 metrics
            ch0_valid = adc_ch0 & LUX_VALID_MASK
            if (ch0_valid == 0):
                print("The light data from ch0 is invalid.")
                print("Check connections on the light module")
                return False
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
                print("The light data from ch1 is invalid.")
                print("Check connections on the light module")
                return False
            else:
                ch1_step_num = (adc_ch1 & LUX_STEP_MASK)
                ch1_chord = (adc_ch1 & LUX_CHORD_MASK) >> 4
                ch1_step_val = int(16.5 * ((2**ch1_step_num) - 1))
                ch1_count_val = ch1_chord + (ch1_step_val * ch1_step_num)
                print("adc_ch1 counts = " + str(ch1_count_val))
                # calculate lux value
                R = ch1_count_val / (ch0_count_val - ch1_count_val)
                lux_level = ((adc_ch0 & ~LUX_VALID_MASK) -
                             (adc_ch1 & ~LUX_VALID_MASK)) \
                    * .39 * e**(-.181 * (R**2))
                print("Lux value: " + str(lux_level))
                self.lux = lux_level
                return True
        else:
            print("Lux device is not on.")
            # return False

    def updateHumidity(self, bus):
        print("Reading Humidity...")
        # Create mask for STATUS (first two bits of 64 bit wide result)
        STATUS = 0b11 << 6
        # Currently needs work. Inserting dummy for now.
        TCA_select(bus, self.mux_addr, SensorCluster.humidity_chan)
        bus.write_quick(SensorCluster.humidity_addr)  # Begin conversion
        sleep(.25)
        for i in range(3):
            # wait 100ms to make sure the conversion takes place.
            data = bus.read_i2c_block_data(SensorCluster.humidity_addr, 0, 4)
            status = (data[0] & STATUS) >> 6
            if status == 0 or status == 1:
                humidity = round((((data[0] & 0x3f) << 8) |
                                  data[1]) * 100.0 / (2**14 - 2), 3)
                self.humidity = humidity
                temp = (((data[2] << 8) | (data[3] & 0xfc))
                        >> 2) / (2**14 - 2) * 165 - 40
                print("Humidity module temp is " + str(temp))
                return True
        print("Failed to update humidity. Check module connections")
        return False

    def updateSoilMoisture(self, bus):
        # Needs a lot of work. Inserting dummy.
        # This method will work off of the ADC module
        TCA_select(bus, self.mux_addr, SensorCluster.adc_chan)
        moisture = get_ADC_value(
            bus, SensorCluster.adc_addr, SensorCluster.moisture_chan)
        moisture *= 2  # Account for voltage division within moisture sensor
        #               I will look into using ADC gain instead of simply scaling.
        # This will need to be mapped to 0-1 values
        #   based on moisture levels later on
        if (moisture != 0 and moisture < .985):
            self.soil_moisture = moisture
        else:
            print("The soil moisture meter is either off or unplugged.")
        return True

    def updateAcidity(self, bus):
        # Needs a lot of work. Inserting dummy.
        # This method will work off of the ADC module.
        TCA_select(bus, self.mux_addr, SensorCluster.adc_chan)
        self.acidity = "50 (Hardcoded Value)"
        return True

    def updateAllSensors(self, bus):
        """ Method runs through all sensor modules and updates 
            to the latest sensor values.

        After running through each sensor module,
        The sensor head (the I2C multiplexer), is disabled
        in order to avoid address conflicts.
        Usage:
            plant_sensor_object.updateAllSensors(bus_object)
        """
        self.updateTemp(bus)
        self.updateLux(bus)
        self.updateHumidity(bus)
        self.updateSoilMoisture(bus)
        self.updateAcidity(bus)
        self.timestamp = time()
        self.saveAllSensors()
        # disable sensor module
        tca_status = TCA_select(bus, self.mux_addr, "off")
        if tca_status != 0:
            raise Exception(
                "Bus multiplexer was unable to switch off to prevent conflicts")

    def saveAllSensors(self):
        print("Updating sensor data")
        # Saves all of the current sensor values
        # to the webservice Plant object
        try:
            plant = models.Plant.for_slot(self.ID, raise_if_not_found=False)
            if plant:
                plant.sensor_data_points.light(). \
                    build(sensor_value=self.lux).save()
                plant.sensor_data_points.water(). \
                    build(sensor_value=self.moisture).save()
                plant.sensor_data_points.humidity(). \
                    build(sensor_value=self.humidity).save()
                plant.sensor_data_points.acidity(). \
                    build(sensor_value=self.acidity).save()
                plant.sensor_data_points.temperature(). \
                    build(sensor_value=self.temp).save()
            else:
                print("Plant object was not successfully created")
        except:
            print("Unable to store plant data")
