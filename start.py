#!/usr/bin/env python3
"""
智绘图一键启动脚本
用法: python start.py
"""
import subprocess
import sys
import os
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")

def run(cmd, cwd, name):
    print(f"[{name}] 启动: {cmd}")
    return subprocess.Popen(cmd, cwd=cwd, shell=True)

procs = []

# 后端
p1 = run("uvicorn app.main:app --reload --port 8000", BACKEND, "后端")
procs.append(p1)
time.sleep(2)

# 前端
p2 = run("pnpm dev", FRONTEND, "前端")
procs.append(p2)

print("\n后端: http://localhost:8000/docs")
print("前端: http://localhost:5173")
print("\nCtrl+C 停止所有服务\n")

try:
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    for p in procs:
        p.terminate()
    print("\n已停止")
