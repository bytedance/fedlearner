import os
import sys
import zipfile


def add_to_zip(zf, path):
    if os.path.isdir(path):
        for nm in os.listdir(path):
            add_to_zip(zf, os.path.join(path, nm))
    else:  # file
        zf.write(path)


def main(args=None):
    import textwrap
    usage = textwrap.dedent("""\
        Usage:
            zip.py zipfile.zip src ... # Create zipfile from sources
        """)
    if args is None:
        args = sys.argv[1:]

    if len(args) != 2:
        print(usage)
        sys.exit(1)

    with zipfile.ZipFile(args[0], 'w') as zf:
        for path in args[1:]:
            add_to_zip(zf, path)


if __name__ == "__main__":
    main()
