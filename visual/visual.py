#!/usr/bin/python3

# This script will be called from the command line by the user. It will handle all file i/o.

import argparse, os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Minispec(.ms) file containing the function or module to view")
    parser.add_argument("target", help="Name of the function or module to synthesize")
    parser.add_argument("--visualdir", "-s", default="visualDir", help="Folder for intermediate visual files")
    args = parser.parse_args()
    print(args.__repr__())

    print(args.visualdir)

    if not os.path.exists(args.visualdir):
        print("Creating synthesis directory")
        os.makedirs(args.visualdir)
    else:
        # Clean up all files, as multi-module builds sometimes get stale data otherwise
        #run("rm -rf %s/*" % (args.synthdir,))
        pass #TODO erase files

    