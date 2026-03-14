from __future__ import annotations

import sys

from ny_oca_conviction.cli import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "report", *sys.argv[1:]]
    main()
