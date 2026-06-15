import sqlite3
from datetime import datetime

# database name
DB_NAME = "yt-pipeline.db"

# function to connect to database
# -----------------------------------------------------------------------------
def get_connection():
  try:
    # connect to database (30s timeout)
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    # allows other connections to read while writing
    conn.execute("PRAGMA journal_mode=WAL;")
    # treats rows as dictionaries and
    # allows getting data by column name
    conn.row_factory = sqlite3.Row
    return conn
  except sqlite3.Error as e:
    print(f"[DATABASE] Error trying to connect to database: {e}")
    raise

# -----------------------------------------------------------------------------
def init_db():
  # main video table
  query = """
    CREATE TABLE IF NOT EXISTS videos (
      video_id TEXT PRIMARY KEY,
      channel_id TEXT NOT NULL,
      author TEXT NOT NULL,
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
    print(f"[DATABASE] Error trying to initialize database: {e}")
    raise

# -----------------------------------------------------------------------------
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
    print(f"[DATABASE] Error checking status for channel {channel_id}: {e}")
    # false if something went wrong (safety net)
    return false

# -----------------------------------------------------------------------------
def save_rss_videos(video_list: list, author: str):
  # expected format:
  # {
  #   "video_id": '?',
  #   "channel_id": '?',
  #   "author": '?',
  #   "title": '?',
  #   "published_at": '?'
  # }

  # do nothing if the list is empty
  if not video_list:
    return

  # get channel ID from the first element of the list
  # if it is empty it will never get to this point
  # so there will be at least the element [0]
  channel_id = video_list[0]['channel_id']
  # verify if it's the first time adding the channel
  # we don't want to flood the database with the last 15 videos
  # at once, so for new channels we get only the last video
  new_channel = is_new_channel(channel_id)

  # query to insert videos in the database
  # the INSERT OR IGNORE will make sure that we
  # don't have any duplicates from reading the
  # same rss feed over and over
  insert_query="""
    INSERT OR IGNORE INTO videos
    (video_id, channel_id, author, title, published_at, status)
    VALUES (?, ?, ?, ?, ?, ?);
  """

  try:
    # connect to database
    with get_connection() as conn:
      # go through each video in order
      for index, video in enumerate(video_list):
        # if it's the first time adding the channel, skip it
        if new_channel and index > 0:
          status = "skipped"
        # else, goes to the waiting line
        else:
          status = "waiting"

        # inserts video in the database
        conn.execute(
          insert_query, (
            video['video_id'],
            video['channel_id'],
            video['author'],
            video['title'],
            video['published_at'],
            status
          )
        )

      # save changes
      conn.commit()
      print(f"[DATABASE] Added videos from channel [{author}]")
  except aqlite3.Error as e:
    print(f"[DATABASE] Error trying to insert videos in the database: {e}")

# gets all the videos that match the hours passed since upload
# -----------------------------------------------------------------------------
def get_expired_videos(hours_passed: int = 48) -> list:
  # selects all the videos that are waiting to be processed
  query = """
    SELECT * FROM videos
    WHERE status = 'waiting' AND
    datetime(published_at) <= datetime('now', ?);
  """

  try:
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(query, (f"-{hours_passed} hours", ))
      # returns all videos that matches the criteria
      return cursor.fetchall()
  except sqlite3.Error as e:
    print(f"[DATABASE] Error trying to fetch video waitlist: {e}")
    # returns an empty list
    return []

# prints the entire database
# -----------------------------------------------------------------------------
def print_database(show_channel_id: bool = False):
  query = """
    SELECT * FROM videos
    ORDER BY published_at DESC;
  """

  try:
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(query)
      rows = cursor.fetchall()

      # if the database is empty, just return
      if not rows:
        print("[DATABASE] Database empty")
        return

      # set column spacing
      if show_channel_id:
        # | video_id | status | published at | channel_id | author | title |
        header_format = "| {:<11} | {:<9} | {:<18} | {:<24} | {:<24} | {:<45} |"
        total_width = 150
      else:
        # | video_id | status | published_at | author | title |
        header_format = "| {:<11} | {:<9} | {:<18} | {:<24} | {:<45} |"
        total_width = 123

      # block separator
      print("=" * total_width)

      # print table header
      if show_channel_id:
        print(
          header_format.format(
            "VIDEO ID",
            "STATUS",
            "PUBLISHED AT",
            "CHANNEL ID",
            "AUTHOR",
            "TITLE"
          )
        )
      else:
        print(
          header_format.format(
            "VIDEO ID",
            "STATUS",
            "PUBLISHED AT",
            "AUTHOR",
            "TITLE"
          )
        )

      # block separator
      print("=" * total_width)

      for row in rows:
        # truncate titles to 45 characters
        display_title = row['title']
        if len(display_title) > 45:
          display_title = display_title[:42] + "..."

        try:
          clean_date = row['published_at'].split('+')[0]
          converted_date = datetime.fromisoformat(clean_date)
          display_date = converted_date.strftime("%b %d, %Y %Hh%M")
        except ValueError:
          # if anything goes wrong, use the date as it is
          # in the database but truncated to 16 characters
          display_date: row['published_at'][:16]

        
        display_status = row['status'].upper()

        if show_channel_id:
          print(
            header_format.format(
              row['video_id'],
              display_status,
              display_date,
              row['channel_id'],
              row['author'],
              display_title,
            )
          )
        else:
          print(
            header_format.format(
              row['video_id'],
              display_status,
              display_date,
              row['author'],
              display_title,
            )
          )

  except sqlite3.Error as e:
    print(f"[DATABASE] Error trying to print database: {e}")

# -----------------------------------------------------------------------------
if __name__ == "__main__":
  print_database()



