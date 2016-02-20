#!/usr/bin/python

def test(runs=None):

    import sys
    sys.path.append("/home/pi/git/greenhouse-webservice/")
    import smbus
    import i2c_utility
    import app.models as models
    from app.config import DATABASE
    from sensor_models import SensorCluster, IterList
    from controls import ControlCluster
    from datetime import datetime as dt
    import sensor_models
    from time import sleep
    
    try:
        bus = smbus.SMBus(1)
    except IOError:
        print("Cannot open bus. Ignore if using a virtual environment")

    models.lazy_record.connect_db(DATABASE)
    plant1 = models.Plant.for_slot(1, False)
    plant2 = models.Plant.for_slot(2, False)
    if plant1 is None:
        plant1 = models.Plant.create(name="testPlant1",
                                     photo_url="testPlant.png",
                                     water_ideal=57.0,
                                     water_tolerance=30.0,
                                     light_ideal=50.0,
                                     light_tolerance=10.0,
                                     acidity_ideal=9.0,
                                     acidity_tolerance=1.0,
                                     temperature_ideal=55.5,
                                     temperature_tolerance=11.3,
                                     humidity_ideal=0.2,
                                     humidity_tolerance=0.1,
                                     mature_on=dt(2016, 1, 10),
                                     slot_id=1,
                                     plant_database_id=1)
    if plant2 is None:
        plant2 = models.Plant.create(name="testPlant2",
                                     photo_url="testPlant.png",
                                     water_ideal=57.0,
                                     water_tolerance=30.0,
                                     light_ideal=50.0,
                                     light_tolerance=10.0,
                                     acidity_ideal=9.0,
                                     acidity_tolerance=1.0,
                                     temperature_ideal=55.5,
                                     temperature_tolerance=11.3,
                                     humidity_ideal=0.2,
                                     humidity_tolerance=0.1,
                                     mature_on=dt(2016, 1, 10),
                                     slot_id=2,
                                     plant_database_id=1)

    plant1_sense = SensorCluster(ID=1, mux_addr=0x70)
    plant2_sense = SensorCluster(ID=2, mux_addr=0x71)
    print("Plant sensor clusters have successfully been created with IDs: " +
          str(plant1_sense.ID) + "," + str(plant2_sense.ID))

    plant1_control = ControlCluster(1)
    plant2_control = ControlCluster(2)
    print("Plant control clusters have been created with IDs: " +
          str(plant1_control.ID) + "," + str(plant2_control.ID))

    print("Updating sensor data for plant 1")
    if plant1_sense.update_instance_sensors(bus, opt="all") == False:
        print("Plant 1 failed to update.")
    print("Updating sensor data for plant 2")
    if plant2_sense.update_instance_sensors(bus, opt="all") == False:
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
    SensorCluster.update_all_sensors(bus)

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
                SensorCluster.update_all_sensors(bus)
                print(str(cycle) + "," + str(plant1_sense.temp) + "," + str(
                    plant2_sense.temp) + "," + str(plant1_sense.humidity) + "," +
                    str(plant2_sense.humidity) + "," + str(plant1_sense.lux) + "," + 
                    str(plant2_sense.lux) + "," + str(plant1_sense.soil_moisture) + 
                    "," + str(plant2_sense.soil_moisture))
            except IOError:
                print("Run: " + str(cycle) +
                      " - There was a bus error. Continuing test run.")
                print("If the issue persists, check connections and rerun.")
