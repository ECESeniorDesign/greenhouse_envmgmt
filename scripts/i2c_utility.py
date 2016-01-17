#!/usr/bin/python
# This file contains utility functions used to select 
# 	channels via the I2C Multiplexer or the ADC


def TCA_select(bus, addr, channel):
	# This function will write to the control register of the TCA module to select 
	# 	the channel that will be exposed on the TCA module.
	# After doing this, the desired module can be used as it would be normally.
	# 	(The caller should use the address of the I2C sensor module.
	#	The TCA module is only written to when the channel is switched.)
	# addr contains address of the TCA module
	# channel specifies the desired channel on the TCA that will be used.
	if addr < 0x70 or addr > 0x77:
		print("The TCA address("+str(addr)+ ") is invalid. Aborting")
		return False
	if channel < 0 or channel > 3:
		print("The request channel does not exist. Defaulting to channel 0")
		channel=0
		return 
	else:
		temp1 = bus.write_byte(addr,1 <<channel)
		temp2 = bus.read_byte(addr)
		print("MUX READOUT........" + str(temp2))
		return True

def ADC_control(bus, addr, channel):
	print("The ADC is not yet configured")