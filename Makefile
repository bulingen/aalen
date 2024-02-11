SHELL = /bin/bash

.PHONY: help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

clean: 		## clean workspace
	rm -rf .venv

ros-clean:		## clean ROS build
	rm -rf build install log
	mkdir build install log

install-py:		## setup venv and install py dependencies
	( \
		python3 -m venv .venv; \
		touch .venv/COLCON_IGNORE; \
       	source .venv/bin/activate; \
       	pip install wheel; \
       	python -m pip install -r requirements.txt; \
    )

install: install-py		## install everything (not really, but should be)

start-pigpio:		## start pigpio
	sudo pigpiod

stop-pigpio:		## stop pigpio
	sudo killall pigpiod

# Stolen from https://abyz.me.uk/rpi/pigpio/download.html 
install-pigpio:		## install pigpio in this folder
	( \
		wget https://github.com/joan2937/pigpio/archive/master.zip; \
		unzip master.zip; \
		touch pigpio-master/COLCON_IGNORE; \
		cd pigpio-master; \
		make; \
		sudo make install; \
	)
install-pigpio-service:		## installs pigpio systemd service to run at boot
	( \
		sudo cp services/start-pigpio /usr/bin/start-pigpio; \
		sudo cp services/pigpio.service /etc/systemd/system/pigpio.service; \
		sudo chmod 644 /etc/systemd/system/pigpio.service; \
		sudo systemctl enable pigpio; \
		sudo systemctl start pigpio; \
	)
install-i2c:		## install i2c stuff
	( \
		sudo apt update; \
		sudo apt upgrade -y; \
		sudo apt install -y i2c-tools; \
		sudo usermod -a -G i2c ubuntu; \
		echo "now restart your rpi"; \
	)

.PHONY: spidev-permissions
spidev-permissions:		## setup spidev permissions
	sudo ./scripts/spidev-permissions.sh

start:		## start eel
	ros2 launch eel_bringup eel.launch.py

sim-depth:		## start depth simulation
	ros2 launch eel_bringup sim_depth.launch.py

sim-nav:		## start navigation simulation
	ros2 launch eel_bringup sim_navigation.launch.py

start-tanks:		## start tanks launch file
	ros2 launch eel_bringup tanks.launch.py

start-pid:		## start pid launch file
	ros2 launch eel_bringup pid.launch.py

start-gunthix:		## start gunthix launch file
	ros2 launch eel_bringup gunthix.launch.py

build-sym:		## build with symlink
	colcon build --symlink-install

install-depth-sensor:		## install stuff needed for depth senson
	( \
		wget https://github.com/bluerobotics/ms5837-python/archive/refs/heads/master.zip -O depth-lib.zip; \
		unzip depth-lib.zip; \
		touch ms5837-python-master/COLCON_IGNORE; \
		source .venv/bin/activate; \
		pip install ms5837-python-master/; \
	)

install-modem:		## Steps on how to install modem both software and service file for auto connecting
	@( \
		echo "Run these commands:"; \
		echo "cd ./scripts"; \
		echo "sudo ./install_modem_software.sh"; \
		echo ""; \
		echo "Wait for reboot, then run"; \
		echo "cd ./scripts"; \
		echo "sudo ./install_modem_service.sh"; \
	)

install-voltage-sensor:		## install stuff needed for depth senson
	( \
		wget https://github.com/e71828/pi_ina226/archive/refs/heads/main.zip -O voltage-lib.zip; \
		unzip voltage-lib.zip; \
		touch pi_ina226-main/COLCON_IGNORE; \
		source .venv/bin/activate; \
		pip install pi_ina226-main/; \
	)

detect-i2c:		## detect i2c
	sudo i2cdetect -y 1

test-py:		## run tests specific to eel only
	source source_me.sh && pytest src/eel/test/eel

test: test-py		## run all tests
