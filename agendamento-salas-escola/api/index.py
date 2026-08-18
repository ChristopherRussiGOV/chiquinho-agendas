import sys
import os

# Garante que a raiz do projeto esteja no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: F401 — Vercel usa este objeto WSGI
