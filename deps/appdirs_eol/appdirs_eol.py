import sys
from pathlib import Path

import metadata_please
from packaging.requirements import Requirement

def main():
    basic_metadata = metadata_please.basic_metadata_from_source_checkout(Path.cwd())
    for req in basic_metadata.reqs:
        r = Requirement(req)
        if r.name == "appdirs":
            print("Appdirs should be replaced with platformdirs")
            sys.exit(99)

if __name__ == "__main__":
    main()
