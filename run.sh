#!/bin/bash

export FLASK_APP=app
export PYTHONUNBUFFERED=1

# Find free port and start Flask
python3 -c '
import socket
from contextlib import closing
import random
import os

def find_free_port(start_range=5000, end_range=9000):
    while True:
        port = random.randint(start_range, end_range)
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind(("", port))
                return port
            except OSError:
                continue

port = find_free_port()
print(f"\nStarting Flask on port {port}")
print(f"Access the application at: http://localhost:{port}\n")
os.system(f"flask run --port={port}")
'
