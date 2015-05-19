import re

from colors import Color

colours = {
    "red": Color(255, 0, 0),
    "blue": Color(0, 0, 255),
    "green": Color(0, 255, 0),
    "purple": Color(127, 0, 255),
    "white": Color(255, 255, 255),
    "default": "\x01"
}

re_colourize = re.compile("c=\(([a-z]+)\)")


def replace_colour(match):
    if match.group(1) in colours:
        return str(colours[match.group(1)])
    return ""


def colourize(message):
    return re_colourize.sub(replace_colour, message)