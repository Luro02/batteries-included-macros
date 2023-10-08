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
```
