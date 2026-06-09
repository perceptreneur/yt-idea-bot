import sqlite3
import os

# database name
DB_NAME = "yt-pipeline.db"

# function to connect to database
def get_connection():
  try:
    # connect to database (30s timeout)
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    # allows other connections to read while writing
    conn.execute("PRAGMA journal_mode=WAL;")
    # treat rows as dictionaries
    conn.row_factory = sqlite3.Row
    return conn
  except sqlite3.Error as e:
    print(f"Database Connection Error: {e}")
    raise

def init_db():
  # main video table
  query = """
    CREATE TABLE IF NOT EXISTS videos (
      video_id TEXT PRIMARY KEY,
      channel_id TEXT NOT NULL,
      title TEXT NOT NULL,
      published_at TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('waiting', 'processed', 'skipped'))
    );
  """

  try: 
    with get_connection() as conn:
      # create table
      conn.execute(query)
      # save changes
      conn.commit()
  except sqlite3.Error as e:
    print(f"Database Initialization Error: {e}")
    raise

def is_new_channel(channel_id: str) -> bool:
  # select all videos from a specific channel ID
  query = "SELECT COUNT(*) FROM videos WHERE channel_id = ?;"
  
  try:
    with get_connection() as conn:
      # cursor -> alows operations in sqlite
      cursor = conn.cursor()
      # search for any videos with that channel ID
      cursor.execute(query, (channel_id, ))
      # get the video count
      count = cursor.fetchone()[0]
      # true if count equals 0
      return count == 0
  except sqlite3.Error as e:
    print(f"Error Checking Channel Status for Channel {channel_id}: {e}")
    # false if something went wrong (safety net)
    return false

def save_rss_videos(video_list: list):
  # do nothing if the list is empty
  if not video_list:
    return
  
  print("DB PRINT -----")

  for video in video_list:
    print(video)

  print("DB PRINT -----")

