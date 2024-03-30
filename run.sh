#!/usr/bin/bash

# Check for any lazy distros who haven't migrated away from the sunset python 2
if [ -x "$(command -v python3)" ]; then
  PYTHON=python3
else
  PYTHON=python
fi

if [ -d ./venv ]; then
  echo "Found Python venv"
else
  echo "No present python venv, generating. . ."
  $PYTHON -m venv venv

  # activate the venv, and install packages with pip
  echo "Installing packages. . ."
  source ./venv/bin/activate
  $PYTHON -m pip install -r requirements.txt  

  # grab the python path version
  PYTHON_VER=$($PYTHON --version | tr "[:upper:]" "[:lower:]" | tr -d " " | cut -f1-2 -d ".")
  echo $PYTHON_VER

  # patch python steam because it's broken
  echo "Patching python package steam"
  echo "You can undo this patch by running the following:"
  echo "'patch -R patch -d ./venv/lib/${PYTHON_VER}/site-packages/steam/client < cdn_patch.diff'"
  patch -d ./venv/lib/${PYTHON_VER}/site-packages/steam/client < cdn_patch.diff

  # exit the venv when done
  deactivate
fi

# Activate the venv, and run the server
echo "Starting the server. . ."
source ./venv/bin/activate

nohup $PYTHON -m flask run --host=0.0.0.0 &
echo "Server is running."

deactivate

