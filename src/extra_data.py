import sys
import math
import logging
import types

# ensure that the script is run with a relatively modern python version
if sys.version_info.major != 3:
    raise EnvironmentError("python 3 is required for execution of %s" % sys.argv[0])

# In python it is possible to change functions of objects.
#
# This function modifies the object's get_status function, so that
# after calling it, the get_extra_values function is called and all
# values are appended to the result.
def override_get_status(object, get_extra_values):
    # keep a reference to the original get_status function (to call it)
    original_get_status = object.get_status

    def new_get_status(self, eventtime):
        # call the original function
        res = dict(original_get_status(eventtime))
        res.update(get_extra_values(eventtime))
        return res
    
    # replace the old get_status function with the new one
    object.get_status = types.MethodType(new_get_status, object)

class ExtraData:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.config = config

        is_read_only = self.config.getboolean("is_read_only", default=False)

        # extruder is not available in __init__ which is required to override the get_status function
        # therefore it is overridden when klipper connects to the printer.
        self.has_updated = False
        self.printer.register_event_handler("klippy:connect", self._handle_connect)

        # get values from config:
        extruder_section = self.config.getsection("extruder")
        self.nozzle_diameter = extruder_section.getfloat('nozzle_diameter', 0.4, above=0.)
        self.filament_diameter = extruder_section.getfloat('filament_diameter', 1.75, minval=self.nozzle_diameter)

        # register commands:
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('DEBUG_EXTRUDER_VALUES', self.cmd_DEBUG_EXTRUDER_VALUES, desc=self.cmd_SET_DEBUG_EXTRUDER_VALUES_help)
        if not is_read_only:
            self.gcode.register_command('SET_NOZZLE_DIAMETER', self.cmd_SET_NOZZLE_DIAMETER, desc=self.cmd_SET_NOZZLE_DIAMETER_help)
            self.gcode.register_command('SET_FILAMENT_DIAMETER', self.cmd_SET_FILAMENT_DIAMETER, desc=self.cmd_SET_FILAMENT_DIAMETER_help)

    def _handle_connect(self):
        if not self.has_updated:
            # the extruder object is not available in __init__, therefore the get_status method is overridden here
            extruder = self.printer.lookup_object("extruder")
            override_get_status(extruder, lambda eventtime: { "nozzle_diameter": self.nozzle_diameter, "filament_diameter": self.filament_diameter })
            self.has_updated = True

    def get_status(self, eventtime):
        bed_mesh_section = self.config.getsection('bed_mesh')

        return {
            "probe_count": bed_mesh_section.getintlist('probe_count', (3, 3)),
        }
    
    # Update the extruder values based on the new nozzle_diameter/filament_diameter:
    def _update_extruder_values(self, extruder, nozzle_diameter=None, filament_diameter=None):
        # update nozzle_diameter:
        if nozzle_diameter is not None:
            extruder.nozzle_diameter = nozzle_diameter

        extruder_section = self.config.getsection(extruder.name)
        # fetch the value for the filament diameter:
        if filament_diameter is None:
            filament_diameter = self.filament_diameter

        extruder.filament_area = math.pi * (filament_diameter * .5)**2
        def_max_cross_section = 4. * extruder.nozzle_diameter**2
        def_max_extrude_ratio = def_max_cross_section / extruder.filament_area
        max_cross_section = extruder_section.getfloat(
            'max_extrude_cross_section', def_max_cross_section, above=0.)

        extruder.max_extrude_ratio = max_cross_section / extruder.filament_area
        logging.info("Extruder max_extrude_ratio=%.6f", extruder.max_extrude_ratio)
        toolhead = self.printer.lookup_object('toolhead')
        max_velocity, max_accel = toolhead.get_max_velocity()
        extruder.max_e_velocity = extruder_section.getfloat(
            'max_extrude_only_velocity', max_velocity * def_max_extrude_ratio
            , above=0.)
        extruder.max_e_accel = extruder_section.getfloat(
            'max_extrude_only_accel', max_accel * def_max_extrude_ratio
            , above=0.)

    cmd_SET_DEBUG_EXTRUDER_VALUES_help = ("Prints the extruder values that depend on nozzle/filament diameter, useful for debugging.")
    def cmd_DEBUG_EXTRUDER_VALUES(self, gcmd):
        extruder = self.printer.lookup_object("extruder")

        gcmd.respond_info("""
        [extruder]
        nozzle_diameter: {}
        filament_diameter: {}
        filament_area: {}
        max_extrude_ratio: {}
        max_e_velocity: {}
        max_e_accel: {}
        """.format(
            extruder.nozzle_diameter,
            self.filament_diameter,
            extruder.filament_area,
            extruder.max_extrude_ratio,
            extruder.max_e_velocity,
            extruder.max_e_accel,
        ))

    cmd_SET_NOZZLE_DIAMETER_help = ("Sets the nozzle diameter to the specified value")
    # SET_NOZZLE_DIAMETER DIAMETER=0.6
    def cmd_SET_NOZZLE_DIAMETER(self, gcmd):
        new_nozzle_diameter = gcmd.get_float('DIAMETER', None, above=0.)
        # do nothing if no diameter has been specified
        if new_nozzle_diameter is None:
            return

        configfile = self.printer.lookup_object('configfile')
        extruder = self.printer.lookup_object("extruder")

        self._update_extruder_values(extruder, nozzle_diameter=new_nozzle_diameter)
        self.nozzle_diameter = new_nozzle_diameter
        # update config value:
        gcmd.respond_info("extruder: nozzle_diameter: {:.3f}\nThe SAVE_CONFIG command will update the printer config file\nwith the above and restart the printer.".format(new_nozzle_diameter))
        configfile.set("extruder", "nozzle_diameter", "{:.3f}".format(new_nozzle_diameter))

    cmd_SET_FILAMENT_DIAMETER_help = ("Sets the filament diameter to the specified value")
    # SET_FILAMENT_DIAMETER DIAMETER=1.76
    def cmd_SET_FILAMENT_DIAMETER(self, gcmd):
        new_diameter = gcmd.get_float('DIAMETER', None, minval=self.nozzle_diameter)
        # do nothing if no diameter has been specified
        if new_diameter is None:
            return

        configfile = self.printer.lookup_object('configfile')
        extruder = self.printer.lookup_object("extruder")

        self._update_extruder_values(extruder, filament_diameter=new_diameter)
        self.filament_diameter = new_diameter
        # update config value:
        gcmd.respond_info("extruder: filament_diameter: {:.3f}\nThe SAVE_CONFIG command will update the printer config file\nwith the above and restart the printer.".format(new_diameter))
        configfile.set("extruder", "filament_diameter", "{:.3f}".format(new_diameter))


def load_config(config):
    return ExtraData(config)
