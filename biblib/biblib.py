import threading
import socket
import time
import traceback
from datetime import datetime
from collections import deque

from . import event


class IRCEvents:
    def __init__(self):
        self.Connected = event.Event()
        self.Disconnected = event.Event()
        self.Msg = event.Event()
        self.ChanMsg = event.Event()
        self.PrivMsg = event.Event()
        self.Join = event.Event()
        self.Part = event.Event()
        self.Quit = event.Event()
        self.Nick = event.Event()
        self.CTCP = event.Event()
        self.Raw = event.Event()
        self.Numeric = event.Event()


class Bot:
    def __init__(self, address, nick, mode=0, realname=None, usessl=None):
        self.recv_thread = threading.Thread(target=self.receive_manager, name="receive-thread")
        self.send_thread = threading.Thread(target=self.send_manager, name="send-thread")
        self.address = address
        self.mode = mode
        self.nick = nick
        self.realname = realname if realname is not None else self.nick
        self.events = IRCEvents()
        self.messagequeue = deque()
        self.tsocket = socket.socket()
        self.enabled = False
        if usessl is not None:
            try:
                import ssl
            except ImportError:
                self.print("Unable to initiate SSL for this server")
            else:
                self.tsocket = ssl.wrap_socket(self.tsocket)
        self.fsocket = self.tsocket.makefile()

    def connect(self):
        self.enabled = True
        self.tsocket.connect(self.address)
        self.print(self.tsocket)
        self.send("NICK {}".format(self.nick))
        self.send("USER {} {} * :{}".format(self.nick, self.mode, self.realname))
        self.recv_thread.start()
        self.send_thread.start()

    def join(self, channel):
        message = "JOIN {}".format(channel)
        self.send(message)

    def part(self, channel, message=""):
        self.print(message)
        message = "PART {} :{}".format(channel, message)
        self.send(message)

    def action(self, target, message):
        self.privmsg(target, "\x01ACTION {}\x01".format(target, message))

    def privmsg(self, target, message):
        info = "PRIVMSG {} :".format(target)
        messagelength = 510 - len(info)
        while True:
            self.send("{}{}".format(info, message[:messagelength]))
            if len(message) > messagelength:
                message = message[messagelength:]
            else:
                break

    def notice(self, target, message):
        info = "NOTICE {} :".format(target)
        messagelength = 510 - len(info)
        while True:
            self.send("{}{}".format(info, message[:messagelength]))
            if len(message) > messagelength:
                message = message[messagelength:]
            else:
                break

    def mode(self, channel, mode, message):
        message = "MODE {} {} {}".format(channel, mode, message)
        self.send(message)

    def send(self, message):
        self.messagequeue.appendleft(message)

    @staticmethod
    def print(message):
        print("[{}] {}".format(datetime.now().replace(microsecond=0), message))

    def send_manager(self):
        while self.enabled:
            if len(self.messagequeue) > 0:
                message = self.messagequeue.pop()
                self.print(message)
                try:
                    self.tsocket.send(bytes(message + "\r\n", "utf-8"))
                except OSError:
                    self.print(traceback.format_exc())
                    self.enabled = False
                    self.events.Disconnected()
            time.sleep(0.5)

    def receive_manager(self):
        while self.enabled:
            try:
                data = self.fsocket.readline().rstrip("\r\n")
                if not data:
                    time.sleep(0.1)
                    continue
                self.print(data)
                self.parse_message(data)
            except OSError:
                self.print(traceback.print_exc())
                self.enabled = False
                self.events.Disconnected()
            time.sleep(0.01)

    def parse_message(self, message):
        self.events.Raw(message)
        command = message.split(" ")
        command[0] = command[0].lstrip(":")
        if command[0] == "PING":
            command[1] = command[1].lstrip(":")
            self.send("PONG {}".format(" ".join(command[1:])))
        elif command[1] == "PRIVMSG" or command[1] == "NOTICE":
            command[3] = command[3].lstrip(":")
            if command[3].startswith("\x01") and message.endswith("\x01"):
                self.events.CTCP(command[2], command[0], command[3].strip("\x01"), " ".join(command[4:]).rstrip("\x01"))
            else:
                message = "{}".format(command[3], " ".join(command[3:]))
                self.events.PrivMsg(command[0], message)
                if command[2].startswith("#"):
                    self.events.ChanMsg(command[2], command[2], message)
                elif command[2] == self.nick:
                    self.events.PrivMsg(command[2], message)
        elif command[1].isnumeric():
            self.events.Numeric(int(command[1]), " ".join(command[2:]))
            if command[1] == "001":
                self.events.Connected()
        elif command[1] == "JOIN":
            self.events.Join(command[2], command[0])
        elif command[1] == "PART":
            self.events.Part(command[2], command[0])
        elif command[1] == "QUIT":
            self.events.Quit(command[2], command[0])
        elif command[1] == "NICK":
            self.events.Nick(command[0], command[2])