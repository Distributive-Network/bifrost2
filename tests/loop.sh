#!/usr/bin/env bash

#
# Watch for file changes, re-run tests, land on debuggers.
#

find .. -name "*.py" -o -name "*.js" | entr -c sh -c 'poetry run pytest --color=yes -s'

