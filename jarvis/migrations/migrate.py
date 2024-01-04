import inspect
import re
import sys
from importlib import import_module
from pathlib import Path

from pyttman import app
from jarvis.models import MigrationVersion


if __name__ == "__main__":
    # Set the path base dir to the current working directory
    # so that the migrations module can be imported.

    migrations_dir = Path(app.settings.APP_BASE_DIR) / "migrations"
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Could not find migrations directory: "
                                f"{migrations_dir.as_posix()}")

    sys.path.append(migrations_dir.as_posix())

    args = set(sys.argv[1:])
    if "current" in args:
        # fill with zeros to 8 digits
        print(f"{MigrationVersion.objects.first().version:08d}")
        exit(0)

    steps_limit = sys.argv[-1]
    steps_limit = re.sub("[+-]", "", steps_limit)
    if steps_limit.isdigit():
        steps_limit = abs(int(steps_limit))
    else:
        steps_limit = None

    if (version_cursor := MigrationVersion.objects.first()) is None:
        version_cursor = MigrationVersion.objects.create()

    current_version = file_version = version_cursor.version
    upgrade = "upgrade" in args
    downgrade = "downgrade" in args
    performed_migrations = 0

    if upgrade:
        migration_files = migrations_dir.glob("*.py")
    elif downgrade:
        migration_files = reversed(list(migrations_dir.glob("*.py")))
    else:
        print("Please specify either 'upgrade' or 'downgrade' as an argument.")
        exit(0)

    print("Running migrations...")

    for migration_file in migration_files:
        if migration_file.name.startswith("00000000"):
            continue
        elif migration_file.name == "migrate.py":
            continue

        try:
            file_version_str = migration_file.name.split("_")[0]
            file_version = int(file_version_str)
        except ValueError:
            raise ValueError(f"Could not parse version from migration file: "
                             f"{migration_file.as_posix()}")

        if upgrade and file_version > current_version:
            method = "upgrade"
        elif downgrade and file_version < current_version:
            method = "downgrade"
        else:
            continue

        migration_module = import_module(migration_file.stem)
        func = getattr(migration_module, method)
        print(f" >> Running {method} in migration {file_version_str}: "
              f"'{inspect.getdoc(migration_module)}'")
        func()
        performed_migrations += 1
        version_cursor.version = file_version
        version_cursor.save()

        if steps_limit is not None and performed_migrations >= steps_limit:
            break

    if performed_migrations == 0:
        print("\nNo migrations to perform.")
    else:
        print(f"\nPerformed {performed_migrations} migrations.")
