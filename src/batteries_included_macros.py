import sys

# ensure that the script is run with a relatively modern python version
if sys.version_info.major != 3:
    raise EnvironmentError("python 3 is required for execution of %s" % sys.argv[0])

class BatteriesIncludedMacros:
    is_debug: bool

    def __init__(self, config):
        self.printer = config.get_printer()
        self.config = config
        # make extra data available to gcode macros:
        self.printer.add_object("extra", self)

        self.is_debug = config.getboolean("is_debug", default=False)


        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('TEST_BATTERIES_INCLUDED', self.cmd_TEST_BATTERIES_INCLUDED, desc=self.cmd_TEST_BATTERIES_INCLUDED_help)
        self.gcode.register_command('_PARSE_MARLIN_PARAMS', self.cmd_PARSE_MARLIN_PARAMS, desc=self.cmd_PARSE_MARLIN_PARAMS_help)

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

    def _list_commands(self) -> list[str]:
        # gcode_handlers is a dict[name, function]
        # calling sorted on a dict, will only return the sorted keys
        return list(sorted(self.gcode.gcode_handlers))

    cmd_PARSE_MARLIN_PARAMS_help = ("Translates marlin params into klipper params")
    def cmd_PARSE_MARLIN_PARAMS(self, gcmd):
        target = gcmd.get('TARGET', default=None)
        if target is None:
            raise gcmd.error("TARGET must be specified")

        if target not in self._list_commands():
            raise gcmd.error(f"The command TARGET='{target}' is not known.")

        args = str(gcmd.get('ARGS', default=""))

        # This parses the args by first removing trailing comments with ; and '#', then splitting
        # the result by whitespace (to obtain a list of arguments)
        parsed_params = args.split(';', 1)[0].split('#', 1)[0].lower().split()

        if self.is_debug:
            gcmd.respond_info(f"ARGS: {args}, parsed: {parsed_params}")

        macro_arguments = {}
        for param in parsed_params:
            if len(param) > 1:
                macro_arguments[param[0:1]] = param[1:]
            else:
                # flags are set to true:
                macro_arguments[param] = "true"

        final_arguments = " ".join([f"{k}=\"{v}\"" for (k, v) in macro_arguments.items()])
        if self.is_debug:
            gcmd.respond_info(f"Calling: {target} {final_arguments}")

        self.gcode.run_script_from_command(f"{target} {final_arguments}")

def load_config(config):
    return BatteriesIncludedMacros(config)
