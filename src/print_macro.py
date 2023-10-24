import ast
import json
import traceback
import logging

from pathlib import Path
from .gcode_macro import (
    TemplateWrapper,
    PrinterGCodeMacro,
    GCodeMacro
)

class PrintTemplateWrapper(TemplateWrapper):
    def __init__(self, printer, env, name, script, config):
        self.preview = config.get("preview", None)
        self.preview_dimension = config.get("preview_dimension", "300x300")
        self.time = config.get("time", None)
        self.filament_used = config.get("filament_used", None)
        self.layer_height = config.get("layer_height", None)

        self.config = config

        # the below is copy-paste from the parent (except print_macro instead of gcode_macro)
        self.printer = printer
        self.name = name
        self.gcode = self.printer.lookup_object('gcode')
        gcode_macro = self.printer.lookup_object('print_macro')
        self.create_template_context = gcode_macro.create_template_context

        try:
            self.template = env.from_string(script)
        except Exception as e:
            msg = f"Error loading template '{name}': {traceback.format_exception_only(type(e), e)[-1]}"
            logging.exception(msg)
            raise printer.config_error(msg)

    def run_gcode_from_command(self, context=None):
        # this is the key function that changes how the macro is executed
        # self.gcode.run_script_from_command() does not start a print

        # first generate the gcode
        rendered_gcode = self.render(context)

        # prepare the thumbnail:
        def wrap(string: str, width: int) -> list[str]:
            return [string[i - width:i] for i in range(width, len(string) + width, width)]

        final_gcode = ";FLAVOR:Marlin\n"

        # add extra metadata, depending on what has been given by the macro:
        if self.time is not None:
            final_gcode += f";TIME:{self.time}\n"

        if self.filament_used is not None:
            final_gcode += f";Filament used: {self.filament_used}\n"

        if self.layer_height is not None:
            final_gcode += f";Layer height: {self.layer_height}\n"

        if self.preview is not None:
            # join all the lines of the preview and remove whitespace
            prepared_preview = "".join([line.strip() for line in self.preview.splitlines()])

            image_size = len(prepared_preview)

            thumbnail = "\n".join(["; " + line for line in wrap(prepared_preview, 78)])

            final_gcode += f"""
;Generated with Cura_SteamEngine 5.4.0
;
; thumbnail begin {self.preview_dimension} {image_size}
{ thumbnail }
; thumbnail end
;

"""


        final_gcode += f"{rendered_gcode}\n"

        # give the file the same name as the macro:
        virtual_filename = f"{self.config.get_name().split(maxsplit=1)[1]}.gcode"

        virtual_sdcard = self.printer.lookup_object('virtual_sdcard')

        real_path = Path(virtual_sdcard.sdcard_dirname).joinpath(virtual_filename)

        # write gcode to the file
        with open(real_path, "w+") as fd:
            fd.write(final_gcode)

        # start the print
        self.gcode.run_script_from_command(f"SDCARD_PRINT_FILE FILENAME={virtual_filename}\nK30 {virtual_filename}")

class PrintPrinterGCodeMacro(PrinterGCodeMacro):
    def __init__(self, config):
        super(PrintPrinterGCodeMacro, self).__init__(config)
        self.virtual_sdcard_section = config.getsection('virtual_sdcard')
        self.virtual_sdcard = self.printer.lookup_object('virtual_sdcard')

        # The K30 command deletes a file from the virtual sdcard,
        # commands in klipper are evaluated instantly, so if a gcode contains
        # K30 at the end (to delete it's own file), klipper tries to execute it
        # in the beginning...
        self.reactor = self.printer.get_reactor()
        self.timer_handler = None
        self.file_removal_queue = []

        gcode = self.printer.lookup_object('gcode')
        gcode.register_command('K30', self.cmd_K30)

    # copy-paste from parent class, only change is that
    # PrintTemplateWrapper constructor is called instead of TemplateWrapper
    def load_template(self, config, option, default=None):
        name = f"{config.get_name()}:{option}"

        if default is None:
            script = config.get(option)
        else:
            script = config.get(option, default)

        return PrintTemplateWrapper(self.printer, self.env, name, script, config)

    def _register_callback_in(self, sleep_duration: float, callback):
        def _callback_wrapper(eventtime):
            waketime = callback(eventtime)
            if waketime is None:
                waketime = self.reactor.NEVER
            return waketime

        self.timer_handler = self.reactor.register_timer(
            _callback_wrapper,
            self.reactor.monotonic() + sleep_duration
        )

    def _empty_queue(self, eventtime):
        # check if the printer is using the sdcard (currently printing)
        if not self.virtual_sdcard.is_active():
            # the sd card is not used, therefore the files can be deleted:
            for file in self.file_removal_queue:
                file.unlink(missing_ok=True)

            self.file_removal_queue.clear()
            if self.timer_handler is not None:
                # disable the currently scheduled timer:
                self.reactor.update_timer(self.timer_handler, self.reactor.NEVER)
                self.timer_handler = None

            return

        # the sd card is currently unavailable, therefore schedule a wakeup:

        # approximate when the print will be over:
        elapsed_time = self.printer.lookup_object('idle_timeout').get_status(eventtime)["printing_time"]
        progress = self.virtual_sdcard.progress()

        # to prevent division by zero
        if progress == 0:
            progress = 1

        total_time = float(elapsed_time) / float(progress)
        next_wakeup = total_time - elapsed_time

        # at least 5s should elapse, before the next call:
        if next_wakeup < 5.0:
            next_wakeup = 5.0

        # next_wakeup should be at most 60mins away:
        if next_wakeup > 60.0 * 60.0:
            next_wakeup = 60.0 * 60.0

        # if less than 5% of the print have been done, use a fixed timer instead:
        if progress < 0.05:
            next_wakeup = 30.0

        # if a wakeup is already pending, just update the wakeup time:
        if self.timer_handler is not None:
            self.reactor.update_timer(self.timer_handler, self.reactor.monotonic() + next_wakeup)
            return

        self._register_callback_in(next_wakeup, lambda eventtime: self._empty_queue(eventtime))

    def cmd_K30(self, gcmd):
        # Delete SD file
        filename = gcmd.get_raw_command_parameters().strip()
        if filename.startswith('/'):
            filename = filename[1:]

        if self.virtual_sdcard.current_file == filename:
            self.virtual_sdcard._reset_file()

        sdcard_dir = Path(self.virtual_sdcard.sdcard_dirname)

        # ensure that the file is in the sdcard_dir before deleting
        #
        # This should prevent gcodes like M30 ../../somefile
        if len([e for e in sdcard_dir.iterdir() if e.is_file() and e.name == filename]) == 0:
            raise gcmd.error(f"File '{filename}' not found on sdcard")

        file_path: Path = sdcard_dir.joinpath(filename)

        # register the file for removal:
        self.file_removal_queue.append(file_path)

        # try to empty queue (if not possible, because a print is running, it will postpone deletion until it the print is done)
        self._empty_queue(self.reactor.monotonic())


def load_config(config):
    return PrintPrinterGCodeMacro(config)

class PrintMacro(GCodeMacro):
    def __init__(self, config):
        if len(config.get_name().split()) > 2:
            raise config.error(f"Name of section '{config.get_name()}' contains illegal whitespace")
        # get the <macro name>: [print_macro <macro name>]
        name = config.get_name().split(maxsplit=1)[1]

        self.alias = name.upper()
        self.printer = printer = config.get_printer()
        # this line loads the PrintPrinterGCodeMacro and calls load_config if necessary
        gcode_macro = printer.load_object(config, 'print_macro')

        self.template = gcode_macro.load_template(config, 'gcode')
        self.gcode = printer.lookup_object('gcode')
        self.rename_existing = config.get("rename_existing", None)
        self.cmd_desc = config.get("description", "G-Code macro")

        if self.rename_existing is not None:
            if (self.gcode.is_traditional_gcode(self.alias) != self.gcode.is_traditional_gcode(self.rename_existing)):
                raise config.error(f"G-Code macro rename of different types ('{self.alias}' vs '{self.rename_existing}')")

            printer.register_event_handler("klippy:connect", self.handle_connect)
        else:
            self.gcode.register_command(self.alias, self.cmd, desc=self.cmd_desc)
        self.gcode.register_mux_command("SET_GCODE_VARIABLE", "MACRO",
                                        name, self.cmd_SET_GCODE_VARIABLE,
                                        desc=self.cmd_SET_GCODE_VARIABLE_help)

        self.in_script = False
        self.variables = {}
        prefix = 'variable_'
        for option in config.get_prefix_options(prefix):
            try:
                literal = ast.literal_eval(config.get(option))
                json.dumps(literal, separators=(',', ':'))
                self.variables[option[len(prefix):]] = literal
            except (SyntaxError, TypeError, ValueError) as e:
                raise config.error(f"Option '{option}' in section '{config.get_name()}' is not a valid literal: {e}")

def load_config_prefix(config):
    return PrintMacro(config)
