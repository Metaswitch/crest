#! /bin/bash
$1/bin/python bootstrap.py
retval=$?
if [[ $retval != 0 ]]; then
  echo -e "\n\nFailed to retrieve some third party Python packages.\nThis is usually caused by http://pypi.python.org being down.\nSee above for full error output.\n"
fi
exit $retval
