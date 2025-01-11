import argparse
import sys

# from argparse import ArgumentParser


def upload(args):
    print("UPLOAD ARGS")


def convert(args):
    print("CONVERT ARGS", args)


# create the top-level parser
parser = argparse.ArgumentParser(
    prog='filelib',
    description='Utilize Filelib API from the command line via FilelibPy',
    epilog='Type filelib -h for help',
    formatter_class=argparse.RawTextHelpFormatter
)
# parser.add_argument("-h", "--help", default=True)
subparsers = parser.add_subparsers(required=True)

# create the parser for the "foo" command
upload_parser = subparsers.add_parser('upload')
# upload_parser.add_argument('-h', type=int, default=1)
upload_parser.add_argument('y', type=float)
upload_parser.set_defaults(func=upload)

# create the parser for the "bar" command
parser_bar = subparsers.add_parser('convert')
parser_bar.add_argument('z')
parser_bar.set_defaults(func=convert)


# parse the args and call whatever function was selected
# args = parser.parse_args('foo 1 -x 2'.split())
# args.func(args)


# parse the args and call whatever function was selected
# args = parser.parse_args('bar XYZYX'.split())
# args.func(args)


def filelib_cli():
    args = sys.argv[1:]
    if not args:
        parser.print_help()
    else:
        _args = parser.parse_args(args)
        _args.func(_args)
        print("ARGS", parser.parse_args())
