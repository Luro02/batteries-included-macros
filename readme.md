batteries-included-macros
===

A collection of klipper macros that just work out of the box.

# Installation

First open a shell on the computer which has klipper install, and then execute the following commands.

Navigate into your home directory
```console
user@pi:~$ cd ~/
```

Clone the repository
```console
user@pi:~$ git clone https://github.com/Luro02/batteries-included-macros
```

Create a link from your home directory into the printer config
```console
user@pi:~$ ln -s ~/batteries-included-macros/config ~/printer_data/config/batteries-included-macros
```

Then open the `~/printer_data/config/moonraker.conf` with an editor like `nano` and add the following code to the end of it:
```console
user@pi:~$ nano ~/printer_data/config/moonraker.conf
```

```ini
[update_manager batteries-included-macros]
type: git_repo
channel: dev
path: ~/batteries-included-macros
origin: https://github.com/Luro02/batteries-included-macros.git
managed_services: klipper
primary_branch: master
install_script: install.sh
is_system_service: False
```

Then edit your `~/printer_data/config/printer.cfg` to include this library:
```ini
[include batteries-included-macros/settings.cfg]
```

Please ensure that the following sections are present (or included) in your `printer.cfg`.
```ini
[firmware_retraction]
#   The length of filament (in mm) to retract when G10 is activated,
#   and to unretract when G11 is activated (but see
#   unretract_extra_length below). The default is 0 mm.
retract_length: 0.5
#   The speed of retraction, in mm/s. The default is 20 mm/s.
retract_speed: 35
#   The length (in mm) of *additional* filament to add when
#   unretracting.
#unretract_extra_length: 0
#   The speed of unretraction, in mm/s. The default is 10 mm/s.
#unretract_speed: 10

[respond]
#default_type: echo
#   Sets the default prefix of the "M118" and "RESPOND" output to one
#   of the following:
#       echo: "echo: " (This is the default)
#       command: "// "
#       error: "!! "
#default_prefix: echo:
#   Directly sets the default prefix. If present, this value will
#   override the "default_type".

[display_status]

[pause_resume]
#recover_velocity: 50.
#   When capture/restore is enabled, the speed at which to return to
#   the captured position (in mm/s). Default is 50.0 mm/s.
```

Depending on your setup, some of those sections might be set in other included configs like `mainsail.cfg`.
