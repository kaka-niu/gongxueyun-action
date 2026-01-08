# Pyarmor 9.2.3 (trial), 000000, 2026-01-08T11:03:39.793817
import sys
import os

# 确保当前目录在模块搜索路径中
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from pyarmor_runtime import __pyarmor__