#!/usr/bin/python

# Contains class information for sensor nodes.
# Each plant is treated as a base, and each plant contains multiple sensors.
# Basic usage:
#   Create a plant record using plant1 = Plant(temp_addr, humidity_addr, lux_addr, adc_addr)
#   Updating individual sensor values can be done with 

# Note that SMBus must be imported and initiated in order to use these classes.
import smbus
from i2c_utility import TCA_select, ADC_control



class SensorCluster(object):
        'Base class for each individual plant - Contains a cluster of various sensors'
        ClusterCount = 0

        def __init__(self, ID, temp_addr, humidity_addr, lux_addr, lux_mux_chan, adc_addr, mux_addr,):
        # Initializes cluster, enumeration, and sets up address info
                self.ID = ID # Plant number specified by caller
                self.temp_addr = temp_addr
                self.humidity_addr = humidity_addr
                self.lux_addr = lux_addr
                self.lux_mux_chan = lux_mux_chan
                self.adc_addr = adc_addr
                self.mux_addr = mux_addr
                self.temp = 0
                self.humidity = 0
                self.lux = 0
                self.soil_moisture = 0
                self.acidity = 0
                SensorCluster.ClusterCount += 1

        def updateAllSensors():
            print("Storing sensor data...")
            try:
                if updateTemp() == False:
                    print("The temperature module failed to update")
                    return False
                if updateLux() == False:
                    print("The light sensor failed to update")
                    return False
                if updateHumidity() == False:
                    print("The humidity sensor failed to update")
                    return False
                if updateSoilMoisture() == False:
                    print("The soil moisture sensor or ADC failed to update")
                    return False
                if updateAcidity() == False:
                    print("The acidity sensor or ADC failed to update")
                    return False
                return True
            except IOError:
                print("Fatal error reading IO. Pass for now (DEV ONLY), as it probably means something just isn't connected.")
                pass

        def updateTemp():
        # Method will update the temp attribute and return the value to the caller
            DEVICE_TEMP_CMD = 0x00 # Command to read temperature
            self.temp = bus.read_byte_data(self.temp_addr, DEVICE_TEMP_CMD)
            #print "Current temperature for Plant " + str(self.num) + "is " + str(temp)
            return True

        def updateLux():
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
                LUX_DEVICE_ADDR = self.lux_addr

                ### Select correct I2C mux channel on TCA module
                TCA_select(self.mux_addr, self.lux_mux_chan)

                ### Make sure lux sensor is powered up.
                bus.write_byte(LUX_DEVICE_ADDR, LUX_PWR_ON)
                lux_on = bus.read_byte_data(LUX_DEVICE_ADDR, LUX_PWR_ON)

                # Check for successful powerup
                if (lux_on == LUX_PWR_ON):
                        ## Send command to initiate ADC on each channel
                        ## Read each channel after the new data is ready
                        print("Reading lux sensor data")
                        bus.write_byte(LUX_DEVICE_ADDR, LUX_READ_CH0)
                        print("....")
                        adc_ch0 = bus.read_byte_data(LUX_DEVICE_ADDR, LUX_READ_CH0)
                        ## Calculate ch0 metrics
                        ch0_valid = adc_ch0 & LUX_VALID_MASK
                        if (ch0_valid==0):
                                print("The light data from ch0 is invalid.")
                                print("Check connections on the light module")
                                return False
                        else:
                                ch0_step_num = (adc_ch0 & LUX_STEP_MASK)
                                ch0_chord =(adc_ch0 & LUX_CHORD_MASK) >> 4 ## Shift to normalize value
                                ch0_step_val = int(16.5*((2**ch0_step_num)-1))
                                ch0_count_val = ch0_chord + (ch0_step_val * ch0_step_num)
                                #print "adc_ch0 = " + str(adc_ch0)
                                #print "adc_ch1 counts = " + str(ch0_count_val)
                                ## Calculate ch1 metrics
                                bus.write_byte(LUX_DEVICE_ADDR, LUX_READ_CH1)
                                adc_ch1 = bus.read_byte_data(LUX_DEVICE_ADDR, LUX_READ_CH1)
                                ch1_valid = adc_ch1 & LUX_VALID_MASK
                                #print "adc_ch1 = " + str(adc_ch1)
                                
                        if (ch1_valid == 0):
                                print("The light data from ch1 is invalid.")
                                print("Check connections on the light module")
                                return False
                        else:
                                ch1_step_num = (adc_ch1 & LUX_STEP_MASK)
                                ch1_chord = (adc_ch1 & LUX_CHORD_MASK) >> 4
                                ch1_step_val = int(16.5*((2**ch1_step_num)-1))
                                ch1_count_val = ch1_chord + (ch1_step_val * ch1_step_num)
                                print("adc_ch1 counts = " + str(ch1_count_val))
                                ## calculate lux value
                                R = ch1_count_val / (ch0_count_val - ch1_count_val)
                                lux_level = ((adc_ch0 & ~LUX_VALID_MASK) -(adc_ch1 & ~LUX_VALID_MASK)) \
                                    * .39 * e**(-.181*(R**2))
                                print("Lux value: " + str(lux_level))
                                self.lux = lux_level
                                return True
                else:
                        print("Lux device is not on.")
                        #return False

        def updateHumidity():
                # Currently needs work. Inserting dummy for now.
                self.humidity = 75
                return True

        def updateSoilMoisture():
                # Needs a lot of work. Inserting dummy.
                # This method will work off of the ADC module
                self.moisture = 50
                return True

        def updateAcidity():
                # Needs a lot of work. Inserting dummy.
                # This method will work off of the ADC module.
                self.acidity = 50
                return True

        def saveAllSensors():
            # Saves all of the current sensor values to the webservice Plant object
            plant = models.Plant.for_slot(self.ID)
            plant.sensor_data_points.light().build(sensor_value=self.lux).save()
            plant.sensor_data_points.water().build(sensor_value=self.moisture).save()
            plant.sensor_data_points.humidity().build(sensor_value=self.humidity).save()
            plant.sensor_data_points.acidity().build(sensor_value=self.acidity).save()
            plant.sensor_data_points.temperature().build(sensor_value=self.temperature).save()
