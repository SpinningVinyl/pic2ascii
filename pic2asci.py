"""add a shebang before this line (e.g. #!/usr/bin/env python)
and make this file executable (chmod +x) if you want to use it
as a Unix command"""

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License,
# or (at your option) any later version.

import argparse
import enum
import math
import sys

from PIL import Image


class MessageType(enum.Enum):
    GENERAL = 0,
    INFO = 1,
    ERROR = 2


class Conversion(enum.Enum):
    AVERAGE = 0,
    LIGHTNESS = 1,
    LUMA1 = 2,
    LUMA2 = 3


class Charset(enum.Enum):
    SHORT = 0,
    LONG = 1,
    BLOCKY = 2


def convert_to_bw(r: int, g: int, b: int, function: Conversion) -> int:
    """Converts RGB triples to grayscale values in the range [0, 255]"""
    # different types of RGB to grayscale conversions
    # I think LUMA1 gives the best results
    switcher = {
        Conversion.AVERAGE:
        int(round((r + g + b) / 3)),
        Conversion.LIGHTNESS:
        int(round((max(r, g, b) + min(r, g, b)) / 2)),
        Conversion.LUMA1:
        int(round(0.21 * r + 0.72 * g + 0.07 * b)),
        Conversion.LUMA2:
        int(round(math.sqrt(0.299 * r * r + 0.587 * g * g + 0.114 * b * b)))
    }
    # if the result is larger than 255, clip it
    return min(switcher.get(function, 0), 255)


def fancy_message(message: str, type: MessageType) -> str:
    """Returns a decorated message according to the MessageType parameter"""
    prefix = ""
    if type == MessageType.INFO:
        prefix = "[i] "
    if type == MessageType.ERROR:
        prefix = "[!] "
    if type == MessageType.GENERAL:
        prefix = "[*] "
    return prefix + message


def new_file_name(fname: str) -> str:
    """Generates output file name if not furnished by the user"""
    file_ext = ".txt"
    last_dot = fname.rfind('.')
    if last_dot == -1:
        return fname + file_ext
    return fname[:last_dot] + file_ext


def get_args() -> argparse.Namespace:
    """Processes the command line arguments and returns an argparse.Namespace object"""
    arg_parser = argparse.ArgumentParser(
        description="Create an ASCII art representation of an image.")
    charset_group = arg_parser.add_mutually_exclusive_group()
    arg_parser.add_argument("image", help="source image")
    arg_parser.add_argument("-o",
                            "--output",
                            type=str,
                            nargs="?",
                            const="~",
                            default="~",
                            help="output file")
    arg_parser.add_argument("-w",
                            "--width",
                            type=int,
                            nargs="?",
                            const="-1",
                            default="-1",
                            help="output width (in characters)")
    charset_group.add_argument("-b",
                               "--blocky",
                               help="use blocky characters (5 shades)",
                               action='store_true')
    charset_group.add_argument(
        "-s",
        "--short",
        help="use short character set (10 shades, default)",
        action='store_true')
    charset_group.add_argument("-l",
                               "--long",
                               help="use long character set (65 shades)",
                               action='store_true')
    arg_parser.add_argument("-i",
                            "--invert",
                            help="optimize for black text on white background",
                            action='store_true')
    return arg_parser.parse_args()


def parse_arguments(args: argparse.Namespace) -> tuple:
    """Parses args and returns their values as a tuple"""
    # if tjhe output file name is not specified,
    # use the name of the image file but with the ".txt" extension
    if args.output == "~":
        output_file_name = new_file_name(args.image)
    # otherwise just use the specified file name
    else:
        output_file_name = args.output

    # set the character set to use
    if args.blocky:
        char_set = Charset.BLOCKY
    elif args.long:
        char_set = Charset.LONG
    else:
        char_set = Charset.SHORT

    # set other parameters
    source_file_name = args.image
    width = args.width
    invert = args.invert

    # return the tuple containing the values
    return (source_file_name, output_file_name, width, char_set, invert)


def process_image(filename: str, output_width: int, char_type: Charset,
                  invert: bool) -> str:
    """Processes the image file and returns the output string"""
    try:
        img = Image.open(filename, mode='r')
    except:
        error_message = fancy_message("Error opening image file " + filename,
                                      MessageType.ERROR)
        print(error_message)
        sys.exit(2)

    print(fancy_message("Image loaded successfully.", MessageType.INFO))

    if img.mode != "RGB":
        print(
            fancy_message("Image mode is not RGB! Converting to RGB...",
                          MessageType.INFO))
        img = img.convert("RGB")

    # resize the image if requested, but only if output_width
    # is less than the actual image width
    output_height = img.height
    if (output_width != -1) and (output_width < img.width):
        output_height = (output_width * img.height) // (img.width * 2)
        # It seems I encountered a bug in Pillow: resize() produces
        # blank images. However, thumbnail() works fine here
    else:
        output_width = img.width
        output_height = img.height // 2
    img = img.resize((output_width, output_height))
    # get the set of characters to use
    char_string = get_char_string(char_type, invert)
    # ensure that we don't get out of bounds
    divisor = math.ceil(255 / (len(char_string) - 1))
    # get the pixel array
    pixels = img.load()
    # get the actual dimensions of the resized image
    width, height = img.size
    print(
        fancy_message(
            f"The output will be {width} characters wide by {height} characters high.",
            MessageType.INFO))
    # iterate over the array and build the output
    print(fancy_message(f"Iterating over the pixels...", MessageType.INFO),
          end=" ")
    output_string = ""
    for y in range(height):
        for x in range(width):
            (r, g, b) = pixels[x, y]
            pixel_value = convert_to_bw(r, g, b, Conversion.LUMA1)
            idx = int(round(pixel_value / divisor))
            char = char_string[idx]
            output_string += char
        output_string += "\n"
    print("Done.")
    img.close()
    return output_string


def save_output(filename: str, output_string: str):
    """Saves `output_string` to file `filename`"""
    try:
        print(fancy_message(f"Saving file {filename}...", MessageType.INFO),
              end=" ")
        output_file = open(filename, mode='w')
        output_file.write(output_string)
        print("Done.")
    except:
        error_message = fancy_message("Error opening output file " + filename,
                                      MessageType.ERROR)
        print("\n" + error_message)
        sys.exit(2)
    finally:
        output_file.close()


def get_char_string(chars: Charset, invert: bool) -> str:
    """Determines which set of characters to use"""
    char_set = ""
    switcher = {
        Charset.SHORT: " .:-=+*%#@",
        Charset.LONG:
        " `^\",:;!il~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
        Charset.BLOCKY: " ░▒▓█"
    }
    char_set = switcher.get(chars, "")
    if invert:
        char_set = char_set[::-1]
    return char_set


def main():
    img_file_name, output_file_name, output_width, char_type, invert = parse_arguments(
        get_args())
    output_string = process_image(img_file_name, output_width, char_type,
                                  invert)
    save_output(output_file_name, output_string)
    print(fancy_message("Have a good day!", MessageType.GENERAL))


if __name__ == "__main__":
    main()
