#! /bin/bash

export POSTGRES_DB=osm_germany
export POSTGRES_USER=thath
export POSTGRES_PORT=5435

python docker/pgosm_flex.py \
    --region=europe \
    --subregion=germany \
    --ram=24 \
    --srid 3035 \
    --skip-verify-checksum \
    --base-path=/home/thath/dev/pgosm-flex/ \
    --layerset-path=/home/thath/dev/pgosm-flex/flex-config/layerset/
