#!/bin/bash

# This script is used to install the python extension
# for klipper. It is used to access functionality that
# klipper does not provide to gcode_macros by default.
#
# For example by default it is not possible to access
# the nozzle_diameter set in the extruder config of the
# printer. The functionality will not be added to klipper
# so a python extension will be used instead.
#
# Related information:
# - https://github.com/Klipper3d/klipper/issues/797
# - https://github.com/Klipper3d/klipper/pull/4123
#
# The shell script itself is based on
# https://github.com/GadgetAngel/voron2_settling_probe

# Force script to exit if an error occurs
set -e

function verify_ready() {
    if [ "$(id -u)" -eq 0 ]; then
        echo "This script must not run as root"
        exit -1
    fi
}

verify_ready

# check that klippy python env is present:
KLIPPY_PYTHON_ENV_ACTIVATE="${HOME}/klippy-env/bin/activate"
if [ ! -f "$KLIPPY_PYTHON_ENV_ACTIVATE" ]; then
    echo "$KLIPPY_PYTHON_ENV_ACTIVATE does not exist."
    exit -2
fi

# activate the python environment:
source $KLIPPY_PYTHON_ENV_ACTIVATE

if [[ $(pip list | grep -F pexpect) ]]; then
    echo "found pexpect installation"
else
    echo "pexpect not installed, installing..."
    pip install --require-virtualenv pexpect
fi

# execute installation script:
python install.py

# deactivate python enviroment
deactivate
