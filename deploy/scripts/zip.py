import os
import sys
import zipfile


def main(args = None):
    import textwrap
    USAGE=textwrap.dedent("""\
        Usage:
            zip.py -l zipfile.zip        # Show listing of a zipfile
            zip.py -t zipfile.zip        # Test if a zipfile is valid
            zip.py -e zipfile.zip target # Extract zipfile into target dir
            zip.py -c zipfile.zip src ... # Create zipfile from sources
        """)
    if args is None:
        args = sys.argv[1:]

    if not args or args[0] not in ('-l', '-c', '-e', '-t'):
        print(USAGE)
        sys.exit(1)

    if args[0] == '-l':
        if len(args) != 2:
            print(USAGE)
            sys.exit(1)
        with zipfile.ZipFile(args[1], 'r') as zf:
            zf.printdir()

    elif args[0] == '-t':
        if len(args) != 2:
            print(USAGE)
            sys.exit(1)
        with zipfile.ZipFile(args[1], 'r') as zf:
            badfile = zf.testzip()
        if badfile:
            print("The following enclosed file is corrupted: {!r}".format(badfile))
        print("Done testing")

    elif args[0] == '-e':
        if len(args) != 3:
            print(USAGE)
            sys.exit(1)

        with zipfile.ZipFile(args[1], 'r') as zf:
            zf.extractall(args[2])

    elif args[0] == '-c':
        if len(args) < 3:
            print(USAGE)
            sys.exit(1)

        def addToZip(zf, path):
            if os.path.isfile(path):
                zf.write(path)
            elif os.path.isdir(path):
                for nm in os.listdir(path):
                    addToZip(zf, os.path.join(path, nm))
            # else: ignore

        with zipfile.ZipFile(args[1], 'w') as zf:
            for path in args[2:]:
                addToZip(zf, path)


if __name__ == "__main__":
    main()
