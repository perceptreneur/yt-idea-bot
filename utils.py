# package imports
from datetime import datetime

# logs messages with timestamps
# -----------------------------------------------------------------------------
def log(message: str):
  # get current time
  current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
  # print message
  print(f"[{current_time}] {message}")

