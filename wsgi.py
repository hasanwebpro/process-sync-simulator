"""WSGI entry point for PythonAnywhere deployment.

In your PythonAnywhere web app dashboard:
  Source code:   /home/<your-username>/process-sync-simulator
  WSGI file:     /home/<your-username>/process-sync-simulator/wsgi.py
  Working dir:   /home/<your-username>/process-sync-simulator

Replace <your-username> with your actual PythonAnywhere username below.
"""

import sys
import os

project_home = '/home/<your-username>/process-sync-simulator'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

from app import app as application
