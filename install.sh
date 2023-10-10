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

KLIPPER_PATH="${HOME}/klipper"
SYSTEMDDIR="/etc/systemd/system"
EXTENSION_NAME="batteries_included_macros.py"
EXTENSION_PATH="src/${EXTENSION_NAME}"
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/ && pwd )"

# verify that klipper is installed
function check_klipper() {
    if [ "$(sudo systemctl list-units --full -all -t service --no-legend | grep -F "klipper.service")" ]; then
        echo "Klipper service found!"
    else
        echo "Klipper service not found, please install Klipper first"
        exit -1
    fi
}

# check if the extension is already installed
function check_installation() {
    local -i is_installed=0

    if [ -e "${KLIPPER_PATH}/klippy/extras/${EXTENSION_NAME}" ]; then
        is_installed=1
    fi

    echo ${is_installed}
}

# link extension to Klipper
function link_extension() {
    echo "Linking extension to Klipper..."
    ln -sf "${SRCDIR}/${EXTENSION_PATH}" "${KLIPPER_PATH}/klippy/extras/${EXTENSION_NAME}"
}

# restart klipper
function restart_klipper() {
    echo "Restarting Klipper..."
    sudo systemctl restart klipper
}

# ensure that the installation script is not ran as root
function verify_ready() {
    if [ "$(id -u)" -eq 0 ]; then
        echo "This script must not run as root"
        exit -1
    fi

    check_klipper
}

while getopts "k:" arg; do
    case ${arg} in
        k) KLIPPER_PATH=${OPTARG} ;;
    esac
done

verify_ready
is_installed=$(check_installation)

# if it is not installed, create a link to the script and restart klipper
if [ ${is_installed} -eq 0 ]; then
    link_extension
    restart_klipper
fi

exit 0
