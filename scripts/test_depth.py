#!/usr/bin/python
import ms5837
import time

sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1 (Raspberry Pi 3)
# sensor = ms5837.MS5837_30BA(0) # Specify I2C bus
# sensor = ms5837.MS5837_02BA()
# sensor = ms5837.MS5837_02BA(0)
# sensor = ms5837.MS5837(model=ms5837.MS5837_MODEL_30BA, bus=0) # Specify model and bus

# We must initialize the sensor before reading it
if not sensor.init():
    print("Sensor could not be initialized")
    exit(1)

# We have to read values from sensor to update pressure and temperature
if not sensor.read():
    print("Sensor read failed!")
    exit(1)

print("pressure {} ".format(sensor.pressure(ms5837.UNITS_atm)))

# print("Pressure: %.2f atm  %.2f Torr  %.2f psi") % (
# sensor.pressure(ms5837.UNITS_atm),
# sensor.pressure(ms5837.UNITS_Torr),
# sensor.pressure(ms5837.UNITS_psi))

print("temp {}".format(sensor.temperature(ms5837.UNITS_Centigrade)))

# print("Temperature: %.2f C  %.2f F  %.2f K") % (
# sensor.temperature(ms5837.UNITS_Centigrade),
# sensor.temperature(ms5837.UNITS_Farenheit),
# sensor.temperature(ms5837.UNITS_Kelvin))

freshwaterDepth = sensor.depth()  # default is freshwater
sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
saltwaterDepth = sensor.depth()  # No nead to read() again
sensor.setFluidDensity(1000)  # kg/m^3
# print("Depth: %.3f m (freshwater)  %.3f m (saltwater)") % (freshwaterDepth, saltwaterDepth)
print(
    "depth {} m (freshwater),  {} (saltwater)".format(freshwaterDepth, saltwaterDepth)
)

# fluidDensity doesn't matter for altitude() (always MSL air density)
# print("MSL Relative Altitude: %.2f m") % sensor.altitude() # relative to Mean Sea Level pressure in air
print("msl relative alt {}".format(sensor.altitude()))

time.sleep(5)

start = time.time()

sensor.setFluidDensity(ms5837.DENSITY_FRESHWATER)
# Spew readings
while True:
    try:
        if sensor.read():
            now = time.time()
            diff = now - start
            # print("diff", diff)
            # print("pressure", sensor.pressure(), "mbar", sensor.pressure(ms5837.UNITS_psi), "temp", sensor.temperature())

            freshwaterDepth = sensor.depth()
            # sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
            # saltwaterDepth = sensor.depth()
            # print(
            #     "depth {} m (freshwater),  {} (saltwater)".format(
            #         freshwaterDepth, saltwaterDepth
            #     )
            # )
            # print("depth", freshwaterDepth)
            # print(
            #     ("Depth: %.3f m (freshwater)  %.3f m (saltwater)")
            #     % (
            #         freshwaterDepth,
            #         saltwaterDepth,
            #     )
            # )

            # print("temp", sensor.temperature())

            our_depth = (freshwaterDepth - 200) / 10

            # print("P: %0.1f mbar  %0.3f psi\tT: %0.2f C  %0.2f F") % (
            print(
                "pressure mbar",
                round(sensor.pressure(), 2),
                "\t",
                "depth m",
                round(freshwaterDepth, 4),
                "\t",
                round(sensor.temperature(), 2),
                "\t",
                round(our_depth, 4),
            )  # Default is mbar (no arguments)
            # sensor.pressure(ms5837.UNITS_psi), # Request psi
            # sensor.temperature(), # Default is degrees C (no arguments)
            # sensor.temperature(ms5837.UNITS_Farenheit)) # Request Farenheit
        else:
            print("Sensor read failed!")
            exit(1)
    except OSError as error:
        print("could not read")
