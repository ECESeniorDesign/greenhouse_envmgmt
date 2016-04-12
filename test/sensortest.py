#!/usr/bin/python

def test(runs=None, same=False):
    """ Method for testing the sensor module.
    Options:
        runs: Allows user to add multiple test points
        same: Forces all greenhouse address to point to the same
                module, allowing only one sensor to be used
    """

    import sys
    sys.path.append("/home/pi/git/greenhouse-webservice/")
    sys.path.append("/home/pi/git/greenhouse_envmgmt/greenhouse_envmgmt")
    import smbus
    import i2c_utility
    import app.models as models
    from app.config import DATABASE
    from sense import SensorCluster, IterList
    from control import ControlCluster
    from datetime import datetime as dt
    from time import sleep
    
    try:
        ControlCluster.bus = smbus.SMBus(1)
        SensorCluster.bus = ControlCluster.bus
    except IOError:
        print("Cannot open bus. Ignore if using a virtual environment")


    plant1_sense = SensorCluster(ID=1, mux_addr=0x70)
    if same == True: # duplicate sensor address if requested 
        plant2_sense = SensorCluster(ID=2, mux_addr=0x70)
    else:
        plant2_sense = SensorCluster(ID=2, mux_addr=0x71)
    print("Plant sensor clusters have successfully been created with IDs: " +
          str(plant1_sense.ID) + "," + str(plant2_sense.ID))

    plant1_control = ControlCluster(1)
    plant2_control = ControlCluster(2)
    print("Plant control clusters have been created with IDs: " +
          str(plant1_control.ID) + "," + str(plant2_control.ID))

    print("Updating sensor data for plant 1")
    if plant1_sense.update_instance_sensors(opt="all") == False:
        print("Plant 1 failed to update.")
    print("Updating sensor data for plant 2")
    if plant2_sense.update_instance_sensors(opt="all") == False:
        print("Plant 2 failed to update")

    print("Outputting sensor data to console...")
    print("....................................")

    print("plant1 temperature is " + str(plant1_sense.temp))
    print("plant2 temperature is " + str(plant2_sense.temp))
    print("plant1 lux is " + str(plant1_sense.lux))
    print("plant2 lux is " + str(plant2_sense.lux))
    print("plant1 humidity is " + str(plant1_sense.humidity))
    print("plant2 humidity is " + str(plant2_sense.humidity))
    print("plant1 Soil Moisture is " + str(plant1_sense.soil_moisture))
    print("plant2 Soil Moisture is " + str(plant2_sense.soil_moisture))
    sleep(1)

    print("Attempting batch sensor update")
    print("Test includes webservice connectivity test")
    SensorCluster.update_all_sensors()

    print("Outputting sensor data to console...")
    print("....................................")

    print("plant1 temperature is " + str(plant1_sense.temp))
    print("plant2 temperature is " + str(plant2_sense.temp))
    print("plant1 lux is " + str(plant1_sense.lux))
    print("plant2 lux is " + str(plant2_sense.lux))
    print("plant1 humidity is " + str(plant1_sense.humidity))
    print("plant2 humidity is " + str(plant2_sense.humidity))
    print("plant1 Soil Moisture is " + str(plant1_sense.soil_moisture))
    print("plant2 Soil Moisture is " + str(plant2_sense.soil_moisture))

    if runs is not None:
        import sys
        print("Creating log file over " + str(runs) + " runs...")
        sys.stdout = open("test_log.txt", "w")
        print("Log file for Greenhouse Sensor testing")
        print("Run #,Plant 1 Temp,Plant 2 Temp,Plant 1 Humidity,Plant 2 Humidity" + 
            ",Plant 1 Lux,Plant 2 Lux,Plant 1 Moisture,Plant 2 Moisture")
        for cycle in range(runs):
            try:
                SensorCluster.update_all_sensors()
                print(str(cycle) + "," + str(plant1_sense.temp) + "," + str(
                    plant2_sense.temp) + "," + str(plant1_sense.humidity) + "," +
                    str(plant2_sense.humidity) + "," + str(plant1_sense.lux) + "," + 
                    str(plant2_sense.lux) + "," + str(plant1_sense.soil_moisture) + 
                    "," + str(plant2_sense.soil_moisture))
            except IOError:
                print("Run: " + str(cycle) +
                      " - There was a bus error. Continuing test run.")
                print("If the issue persists, check connections and rerun.")
