#!/usr/bin/env python3
"""compoundfile command line script.

This module contains command line script for parsing compound files.
"""
import argparse
import json
import pathlib

from .parser import run


def main():
    """Run the command line process to parse a compound file and output pretty printed JSON."""
    parser = argparse.ArgumentParser(description='Parse Microsoft compound file.')
    parser.add_argument('file', metavar='FILE', help='Compound file to parse.')
    args = parser.parse_args()

    target = pathlib.Path(args.file)
    output = run(target)

    print(json.dumps(output, sort_keys=True, indent=4))


if __name__ == '__main__':
    main()
