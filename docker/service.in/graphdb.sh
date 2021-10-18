#!/bin/bash

exec /sbin/setuser cloudkeeper /usr/local/db/bin/arangod --log.output - --database.directory "@GRAPHDB_DATABASE_DIRECTORY@" --server.endpoint "@GRAPHDB_SERVER_ENDPOINT@" --database.password "@GRAPHDB_ROOT_PASSWORD@"
