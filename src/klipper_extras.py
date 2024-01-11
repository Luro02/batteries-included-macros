import re
from pathlib import Path
from typing import Optional

class KlipperExtras:
    has_started: bool

    def __init__(self, config):
        self.printer = config.get_printer()
        self.config = config
        self.gcode = self.printer.lookup_object('gcode')
        self.has_started = False

        self.printer.register_event_handler("klippy:ready", self._handle_ready)

    def rotate_backups(self, folder: Optional[Path], maximum_backups: int = 25):
        # the current printer cfg
        config_path = Path(self.printer.get_start_args()['config_file'])
        backup_file_pattern = re.compile(re.escape(str(config_path.stem)) + r"-\d{7,}_\d{6,}")

        config_folder = config_path.resolve().parent

        if folder is None:
            folder = config_folder / Path("backups/")
        else:
            folder = folder.resolve()

        # create the folder to store logs if it does not exist:
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.gcode.respond_info(f"Failed to open the log folder '{folder}': {str(e)}")
            return

        files_to_move = [path for path in config_folder.iterdir() if path.is_file() and backup_file_pattern.match(path.stem) is not None]

        # move all backups to the dedicated folder:
        for file in files_to_move:
            file.rename(folder / file.name)

        # to prevent the backup folder from growing to infinity, only keep a fixed amount of backups
        for file in sorted([path for path in folder.iterdir() if path.is_file()], key=lambda path: path.name)[:-maximum_backups]:
            file.unlink()

    def _handle_ready(self):
        if self.has_started:
            return

        folder = self.config.get('backup_folder', default=None)
        maximum_backups = self.config.getint('maximum_backups', default=25, minval=1)
        self.rotate_backups(folder, maximum_backups=maximum_backups)

        self.has_started = True

def load_config(config):
    return KlipperExtras(config)
