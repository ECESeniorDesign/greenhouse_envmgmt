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
    from sense import SensorCluster, IterList
    from control import ControlCluster
    from datetime import datetime as dt
    from time import sleep
    
    try:
        ControlCluster.bus = smbus.SMBus(1)
        SensorCluster.bus = ControlCluster.bus
    except IOError:
        print("Cannot open bus. Ignore if using a virtual environment")


    plant1_sense = SensorCluster(ID=1)
    if same == True: # duplicate sensor address if requested 
        plant2_sense = SensorCluster(ID=1)
    else:
        plant2_sense = SensorCluster(ID=2)
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

    print("Plant 1 sensor values")
    print(plant1_sense.sensor_values())
    print("Plant 2 sensor values")
    print(plant2_sense.sensor_values())


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
