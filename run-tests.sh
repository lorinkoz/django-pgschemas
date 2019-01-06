#!/bin/bash

set -e

DATABASE=${DATABASE_HOST:-localhost}
echo "Database: $DATABASE"

while ! nc "$DATABASE" "5432" >/dev/null 2>&1 < /dev/null; do
  i=`expr $i + 1`
    if [ $i -ge 50 ]; then
        echo "$(date) - $DATABASE:5432 still not reachable, giving up."
        exit 1
    fi
    echo "$(date) - waiting for $DATABASE:5432..."
    sleep 1
done
echo "Postgres connection established!"

# TODO: Actually run tests
echo "Nothing done!"
