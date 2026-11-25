"""GCP ACE Exam Trainer — başlatıcı.  Kullanım:  python main.py"""
import sys

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 veya üzeri gerekli.")

try:
    import tkinter  # noqa: F401
except ImportError:
    sys.exit("Tkinter bulunamadı. Windows/macOS'ta python.org kurulumu Tkinter içerir; "
             "Linux'ta: sudo apt install python3-tk")

from examtrainer.gui import main

if __name__ == "__main__":
    main()
