import sys

# ensure that the script is run with a relatively modern python version
if sys.version_info.major != 3:
    raise EnvironmentError("python 3 is required for execution of %s" % sys.argv[0])

class BatteriesIncludedMacros:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.config = config
        # make extra data available to gcode macros:
        self.printer.add_object("extra", self)

        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('TEST_BATTERIES_INCLUDED', self.cmd_TEST_BATTERIES_INCLUDED, desc=self.cmd_TEST_BATTERIES_INCLUDED_help)

    def get_status(self, eventtime):
        bed_mesh_section = self.config.getsection('bed_mesh')
        extruder_section = self.config.getsection("extruder")

        return {
            "probe_count": bed_mesh_section.getintlist('probe_count', (3, 3)),
            "nozzle_diameter": str(extruder_section.getfloat('nozzle_diameter', 0.4)),
            "filament_diameter": str(extruder_section.getfloat('filament_diameter', 1.75)),
        }

    cmd_TEST_BATTERIES_INCLUDED_help = ("A test macro to show that the script is working")
    def cmd_TEST_BATTERIES_INCLUDED(self, gcmd):
        gcmd.respond_info("Macro seems to be working")
        bed_mesh_section = self.config.getsection('bed_mesh')
        extruder_section = self.config.getsection("extruder")

        values = [
            f"probe_count = {bed_mesh_section.getintlist('probe_count', (3, 3))}",
            f"nozzle_size = {extruder_section.getfloat('nozzle_diameter', 0.4)}",
            f"filament_diameter = {extruder_section.getfloat('filament_diameter', 1.75)}",
        ]

        gcmd.respond_info(f"For reference here are some config values: {', '.join(values)}")

def load_config(config):
    return BatteriesIncludedMacros(config)
