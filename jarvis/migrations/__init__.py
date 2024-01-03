import sys

upgrade = downgrade = lambda: None


def expose():
    # Parse args and run the upgrade or downgrade function
    args = set(sys.argv[1:])
    if not {"upgrade", "downgrade"} & args:
        print("Please provide an argument: 'upgrade' or 'downgrade'")
        sys.exit(1)
    elif args & {"upgrade"}:
        print("Running upgrade...")
        upgrade()
    elif args & {"downgrade"}:
        print("Running downgrade...")
        downgrade()
