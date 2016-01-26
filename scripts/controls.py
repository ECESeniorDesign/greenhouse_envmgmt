#!/usr/bin/python

"""
Pin mapping list
	pumpPin = 11
	fan1Pin = 13
	fan2Pin = 16
	light1Pin = 15
	light2Pin = 12
"""

def create_GPIO_dict(ID):
	""" This method creates a dictionary to map plant IDs to
	GPIO pins are associated in triples.
	Each ID gets a light, a fan, and a mist nozzle.
	"""
	

def manage_lights(ID, ideal_per_day, current_total, current_sensor, ideal_sensor):
    light1Pin = 15
    light2Pin = 12
    if ID == 1:
        activePin = light1Pin
    elif ID == 2:
        activePin = light2Pin
    else:
        print("Invalid plant ID")
        return False
    GPIO.setmode(GPIO.BOARD)  # Use board numbering
    GPIO.setup(activePin, GPIO.OUT)
    if current_total < ideal_per_day:
        # The plant has not yet reached it's daily light budget
        if current_sensor <= ideal_sensor:
            # It is currently okay to turn on the light
            GPIO.output(activePin, GPIO.HIGH)
        else:
            GPIO.output(activePin, GPIO.LOW)
    else:
        GPIO.output(activePin, GPIO.LOW)
    return True


def manage_fans(ID, operation):
	""" Usage:
		manageFans(1, "on") # Turn on the fan for plant 1
	"""

    fan1Pin = 13
    fan2Pin = 16
    if ID == 1:
        activePin = fan1Pin
    elif ID == 2:
        activePin = fan2Pin
    else:
        print("Invalid ID")
        return False
    GPIO.setmode(GPIO.BOARD)  # Use board numbering
    GPIO.setup(activePin, GPIO.OUT)
    if operation == "on":
        GPIO.OUTPUT(activePin, GPIO.HIGH)
    else:
        GPIO.OUTPUT(activePin, GPIO.LOW)
    return True


def managePump(ID):
	"""Manages turning on the mist pump based on water data from the plant.
	We will need to aggregate the total amount of water that the plant
	receives so that we can keep track of what it's receiving daily.

	This function will need to select a nozzle to open
	before turning on the mist pump.
	""" 
	activePin = 11
	GPIO.setmode(GPIO.BOARD)  # Use board numbering
    GPIO.setup(activePin, GPIO.OUT)
