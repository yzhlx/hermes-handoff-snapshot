"""Imports required by Learning OS modules that the launcher loads dynamically.

PyInstaller analyzes normal imports but cannot discover imports inside the
hyphenated source files loaded through ``importlib.util.spec_from_file_location``.
Keeping this manifest as normal imports makes the packaged runtime complete
without changing the service's runtime module-loading architecture.
"""

import argparse
import base64
import binascii
import ctypes
from ctypes import wintypes
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import functools
import hashlib
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sqlite3
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlparse
import uuid


# Retain references so static analyzers and packagers keep the imports. The
# application modules consume the same standard-library modules at runtime.
PACKAGED_DYNAMIC_IMPORTS = (
    argparse,
    base64,
    binascii,
    ctypes,
    wintypes,
    ThreadPoolExecutor,
    date,
    datetime,
    timedelta,
    timezone,
    functools,
    hashlib,
    BaseHTTPRequestHandler,
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
    json,
    Path,
    shutil,
    sqlite3,
    threading,
    urllib.error,
    urllib.request,
    parse_qs,
    urlparse,
    uuid,
)
