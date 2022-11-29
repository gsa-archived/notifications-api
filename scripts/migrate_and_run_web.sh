#!/bin/bash

if [[ $CF_INSTANCE_INDEX -eq 0 ]]; then
  flask db upgrade
fi

gunicorn -c ${HOME}/gunicorn_config.py application
