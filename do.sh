#!/usr/bin/env bash
# Do - The Simplest Build Tool on Earth.
# Documentation and examples see https://github.com/8gears/do

set -Eeuo pipefail # -e "Automatic exit from bash shell script on error"  -u "Treat unset variables and parameters as errors"

fmt() {
	poetry run black .
	find . -type f -name "*.py" -exec sed -i -e 's/    /\t/g' {} \;
}


"$@" # <- execute the task

[ "$#" -gt 0 ] || printf "Usage:\n\t./do.sh %s\n" "($(compgen -A function | grep '^[^_]' | paste -sd '|' -))"
