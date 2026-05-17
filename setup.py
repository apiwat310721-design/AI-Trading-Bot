import subprocess
import sys

print("🔧 ติดตั้ง Libraries...")

# ติดตั้ง anthropic
subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic"])

# ติดตั้ง flask
subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])

# ติดตั้ง requests
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])

# ติดตั้ง pandas
subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])

print("✅ ติดตั้งเสร็จแล้ว!")
