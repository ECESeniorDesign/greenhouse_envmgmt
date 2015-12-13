#!/usr/bin/python

import smbus
bus = smbus.SMBus(1) # use i2c port 1

e = 2.71828 # approximate value of e

TEMP_DEVICE_ADDR = 0x48
DEVICE_TEMP_CMD = 0x00
DEVICE_REG_OUT = 0x1d
LUX_DEVICE_ADDR = 0x39
LUX_PWR_ON = 0x03
LUX_PWR_OFF = 0x00
LUX_READ_CH0 = 0x43
LUX_READ_CH1 = 0x83
LUX_VALID_MASK = 0b10000000
LUX_CHORD_MASK = 0b01110000
LUX_STEP_MASK = 0b00001111


#operate on i2c
temp1 = bus.read_byte_data(TEMP_DEVICE_ADDR, DEVICE_TEMP_CMD)
#print '{0:b}'.format(temp)
print "Current temperature for plant0 is " + str(temp1)
temp2 = bus.read_word_data(TEMP_DEVICE_ADDR,DEVICE_TEMP_CMD)
#print "Current temperature for plant1 is " + str(temp2)

### Read light data
bus.write_byte(LUX_DEVICE_ADDR, LUX_PWR_ON)
lux_on = bus.read_byte_data(LUX_DEVICE_ADDR, LUX_PWR_ON)
## If the device is powered on and functioning, lux_on
## Should hold the current device state (on = 0x03)
if (lux_on == LUX_PWR_ON):
    ## Send command to initiate ADC on each channel
    ## Read each channel after the new data is ready
    print "Reading lux sensor data"
    bus.write_byte(LUX_DEVICE_ADDR, LUX_READ_CH0)
    print "...."
    adc_ch0 = bus.read_byte_data(LUX_DEVICE_ADDR, LUX_READ_CH0)
    ## Calculate ch0 metrics
    ch0_valid = adc_ch0 & LUX_VALID_MASK
    if (ch0_valid==0):
	print "The light data from ch0 is invalid."
	print "Check connections on the light module"
    else:
	ch0_step_num = (adc_ch0 & LUX_STEP_MASK)
	ch0_chord =(adc_ch0 & LUX_CHORD_MASK) >> 4 ## Shift to normalize value
	ch0_step_val = int(16.5*((2**ch0_step_num)-1))
	ch0_count_val = ch0_chord + (ch0_step_val * ch0_step_num)
	print "adc_ch0 = " + str(adc_ch0)
	print "adc_ch1 counts = " + str(ch0_count_val)
    ## Calculate ch1 metrics
    bus.write_byte(LUX_DEVICE_ADDR, LUX_READ_CH1)
    adc_ch1 = bus.read_byte_data(LUX_DEVICE_ADDR, LUX_READ_CH1)    
    ch1_valid = adc_ch1 & LUX_VALID_MASK
    print "adc_ch1 = " + str(adc_ch1)
    if (ch1_valid == 0):
	print "The light data from ch1 is invalid."
	print "Check connections on the light module"
    else:
	ch1_step_num = (adc_ch1 & LUX_STEP_MASK)
	ch1_chord = (adc_ch1 & LUX_CHORD_MASK) >> 4
	ch1_step_val = int(16.5*((2**ch1_step_num)-1))
	ch1_count_val = ch1_chord + (ch1_step_val * ch1_step_num)
	print "adc_ch1 counts = " + str(ch1_count_val)
    ## calculate lux value
    R = ch1_count_val / (ch0_count_val - ch1_count_val)
    lux_level = ((adc_ch0 & ~LUX_VALID_MASK) -(adc_ch1 & ~LUX_VALID_MASK)) \
		* .39 * e**(-.181*(R**2))

    print "Lux value: " + str(lux_level)
else:
    print "Lux device is not on."
