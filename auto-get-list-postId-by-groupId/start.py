#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start.py — Entrypoint chính của dự án auto-get-list-postId-by-groupId
Chỉ cần chạy: python start.py

Author  : Khánh Phan / TFY
Version : 2.1.0
"""

import sys
import os

# Thêm thư mục src vào Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from run import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n\033[1;93m[!] Dừng bởi Ctrl+C. Tạm biệt!\033[0m\n")
        sys.exit(0)
