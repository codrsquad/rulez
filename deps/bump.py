import sys

from bumpreqs.cli import main

for filename in sys.argv[1:]:
    main(["--write", filename])
