import os
import inspect
import traceback

from glob import glob
from importlib.machinery import SourceFileLoader

from .biblib import biblib
from configobj import ConfigObj
from validate import Validator
from .plugin_template import IRCPlugin

from . import plugins


def join_script_path(file):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), file)


class Serva(object):
    def __init__(self):
        self.config = None
        self.bot = None
        self.plugins = {}
        self.load()

    def load(self):
        config = ConfigObj(join_script_path("serva.ini"), configspec=join_script_path("config_spec.ini"))
        self.config = config
        config.validate(Validator(), copy=True)
        config.write()
        self.bot = biblib.Bot((config["hostname"], config["port"]), config["name"], usessl=config["ssl"],
                              echo=config["echo"])
        self.bot.events.Connected += self.connected
        self.load_all_plugins()
        self.bot.connect()

    def load_all_plugins(self):
        cwd = os.getcwd()
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        if not os.path.exists("plugins"):
            os.mkdir("plugins")
        for module in glob("plugins/*.py"):
            if module.endswith("__init__.py"):
                continue
            print("Loading {}...{}".format(os.path.basename(module), "done" if self.load_plugin(module) else "failed"))
        os.chdir(cwd)

    def log_error(self):
        print(traceback.format_exc())

    def load_plugin(self, module):
        name = os.path.splitext(os.path.basename(module))[0]
        if name == "__init__":
            return True
        loader = SourceFileLoader(__package__ + ".plugins." + name, module)
        try:
            plugin = loader.load_module()
        except ImportError:
            self.log_error()
            return False
        for i, cls in inspect.getmembers(plugin, inspect.isclass):
            if issubclass(cls, IRCPlugin) and cls is not IRCPlugin:
                self.plugins[name] = cls(self)
                self.plugins[name].load()
                return True
        return False

    def connected(self):
        for channel in self.config["channels"]:
            self.bot.join(channel)

    def unload(self):
        self.bot.disconnect()
        for plugin in self.plugins.values():
            plugin.unload()

if __name__ == "__main__":
    Serva()
