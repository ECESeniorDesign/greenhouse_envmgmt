from distutils.core import setup
setup(
	name = 'greenhouse_envmgmt',
	packages = ['greenhouse_envmgmt'],
	version = '1.0',
	description = 'Sensor and Controls Management for Automated Greenhouse based on I2C',
	author = 'Jeff Baatz',
	url = 'https://github.com/ECESeniorDesign/greenhouse-sensors',
	keywords = ['i2c', 'sensors', 'controls'],
	classifies = [],
	install_requires=['python-smbus']
)

