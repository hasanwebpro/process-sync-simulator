"""WSGI entry point for PythonAnywhere deployment.

In your PythonAnywhere web app dashboard:
  Source code:   /home/HassanBukhari123/process-sync-simulator
  WSGI file:     /home/HassanBukhari123/process-sync-simulator/wsgi.py
  Working dir:   /home/HassanBukhari123/process-sync-simulator
"""

import sys
import os

project_home = '/home/HassanBukhari123/process-sync-simulator'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

from app import app as application
