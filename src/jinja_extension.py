import sys

# ensure that the script is run with a relatively modern python version
if sys.version_info.major != 3:
    raise EnvironmentError("python 3 is required for execution of %s" % sys.argv[0])

class JinjaExtension:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.config = config
        self.gcode = self.printer.lookup_object('gcode')

        # get the main object for the environment: (PrinterGCodeMacro)
        printer_gcode_macro = self.printer.load_object(config, 'gcode_macro')
        environment = printer_gcode_macro.env

        # add custom filters:

        # jinja does not provide a boolean filter, so a filter is added here
        def boolean(value):
            lowercase_value = str(value).lower()
            return lowercase_value in ["true", "1"]

        environment.filters['boolean'] = boolean

def load_config(config):
    return JinjaExtension(config)
