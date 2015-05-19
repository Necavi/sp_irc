import os
import shutil

from configobj import ConfigObj
from validate import Validator

from events.manager import event_manager
from players.helpers import playerinfo_from_userid
from filters.players import PlayerIter
from messages import SayText2
from paths import CFG_PATH

from ..colourizer import colourize
from ..plugin_template import IRCPlugin


def join_script_path(file):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), file)


def parse_event_args(event, args):
    parsed_args = {}
    for arg, argtype in args.items():
        if argtype == "name":
            parsed_args[arg] = playerinfo_from_userid(event.get_int(arg)).get_name()
        elif argtype == "string":
            parsed_args[arg] = event.get_string(arg)
        elif argtype == "int":
            parsed_args[arg] = event.get_int(arg)
        elif argtype == "bool":
            parsed_args[arg] = event.get_bool(arg)
        elif argtype == "float":
            parsed_args[arg] = event.get_float(arg)
    return parsed_args


class SourcePython(IRCPlugin):
    def __init__(self, ins):
        super().__init__(ins)
        self.config_path = CFG_PATH.joinpath("sp_irc.ini")
        if not os.path.exists(self.config_path):
            shutil.copyfile(join_script_path("sp_irc.ini"), self.config_path)
        self.config = ConfigObj(self.config_path, configspec=join_script_path("sp_irc_spec.ini"))
        self.config.validate(Validator(), copy=True)
        self.events = self.config["events"]
        for event in self.events:
            event_manager.register_for_event(event, self.parse_event)
        self.bot.events.ChanMsg += self.irc_message
        self.bot.events.Connected += self.connected

    def parse_event(self, event):
        name = event.get_name()
        if name in self.events:
            args = parse_event_args(event, self.events[name]["args"]) if "args" in self.events[name] else dict()
            self.bot.privmsg(self.config["channel"], self.events[name]["message"].format(**args))

    def unload(self):
        for event in self.events:
            event_manager.unregister_for_event(event, self.parse_event)

    def irc_message(self, source, channel, message):
        for index in PlayerIter(is_filters="all", return_types="index"):
            SayText2(message=colourize(self.config["ingame_format"].format(source=source.split("!")[0], channel=channel,
                                                                           message=message))).send(index)

    def connected(self):
        self.bot.join(self.config["channel"])