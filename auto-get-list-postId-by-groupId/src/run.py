#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

# Paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SRC_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIES_FILE = os.path.join(DATA_DIR, "cookies.txt")
GROUP_IDS_FILE = os.path.join(DATA_DIR, "groupid.txt")

# ANSI COLORS
R = "\033[1;91m"
G = "\033[1;92m"
Y = "\033[1;93m"
B = "\033[1;94m"
M = "\033[1;95m"
C = "\033[1;96m"
W = "\033[1;97m"
X = "\033[0m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    clear()
    print(C + "╔══════════════════════════════════════════════════════╗")
    print(C + "║  " + G + "██████╗ ██╗   ██╗███╗   ██╗" + Y + " AUTO GET POST ID" + C + "        ║")
    print(C + "║  " + G + "██╔══██╗██║   ██║████╗  ██║" + W + " Wrapper → main.py" + C + "       ║")
    print(C + "║  " + G + "██████╔╝██║   ██║██╔██╗ ██║" + M + " By: Khánh Phan / TFY" + C + "    ║")
    print(C + "║  " + G + "██╔══██╗██║   ██║██║╚██╗██║" + B + " Version: 2.1.0" + C + "          ║")
    print(C + "║  " + G + "██║  ██║╚██████╔╝██║ ╚████║" + C + "                          ║")
    print(C + "║  " + G + "╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝" + C + "                          ║")
    print(C + "╚══════════════════════════════════════════════════════╝" + X)
    print()

def load_lines(filepath, label, required=True):
    if not os.path.exists(filepath):
        if required:
            print(R + "[✗] Không tìm thấy: " + filepath + X)
            sys.exit(1)
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    if not lines and required:
        print(R + "[✗] File rỗng: " + filepath + X)
        sys.exit(1)

    print(G + "[✓] " + label + ": " + str(len(lines)) + " dòng" + X)
    return lines

def main():
    banner()
    print(B + "Kiểm tra dữ liệu đầu vào..." + X)
    load_lines(COOKIES_FILE, "Cookies", required=True)
    load_lines(GROUP_IDS_FILE, "Group IDs", required=True)
    
    print(Y + "────────────────────────────────────────────────" + X)
    print(B + "[▶] Bắt đầu khởi chạy bộ máy (index.py)..." + X)
    
    try:
        import subprocess
        index_py = os.path.join(SRC_DIR, "index.py")
        subprocess.run([sys.executable, index_py])
    except KeyboardInterrupt:
        print("\n\n" + Y + "[!] Dừng bởi Ctrl+C. Tạm biệt!" + X + "\n")
        sys.exit(0)
    except Exception as e:
        print("\n" + R + f"[✗] Lỗi khi chạy: {e}" + X + "\n")

if __name__ == "__main__":
    main()
