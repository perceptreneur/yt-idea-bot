# package imports
import sqlite3
from datetime import datetime

# local imports
from utils import log

# database name
DB_NAME = "yt-pipeline.db"

# connects to the database
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
    log(f"[DATABASE] Error trying to connect to database: {e}")
    raise

# initializes the database
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
    log(f"[DATABASE] Error trying to initialize database: {e}")
    raise

# gets the most recent timestamp of a channel
# -----------------------------------------------------------------------------
def get_latest_timestamp(channel_id: str) -> str:
  
  # select the newest video (latest timestamp) of a channel
  query = "SELECT MAX(published_at) FROM videos WHERE channel_id = ?;"

  try:
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(query, (channel_id, ))
      row = cursor.fetchone()

      # return the timestamp string
      # if it exists
      if row and row[0]:
        return row[0]

  except sqlite3.Error as e:
    log(f"[DATABASE] Error fetching timestamp for channel [{channel_id}]")

  return ""

# save rss feed video to the database
# -----------------------------------------------------------------------------
def save_rss_videos(video_list: list, author: str, insert_limit: int = 3):
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

  # query to insert videos in the database
  # the INSERT OR IGNORE will make sure that we
  # don't have any duplicates from reading the
  # same rss feed over and over
  query="""
    INSERT OR IGNORE INTO videos
    (video_id, channel_id, author, title, published_at, status)
    VALUES (?, ?, ?, ?, ?, ?);
  """

  try:
    # get newest video
    latest_timestamp = get_latest_timestamp(channel_id)

    # video from rss feed are already sorted from newest to oldest
    # we sort them again, just in case something weird can happen
    sorted_videos = sorted(
                      video_list,
                      key = lambda x: x['published_at'],
                      reverse = True
                    )
    
    # list of videos to add in the database
    videos_to_insert = []
    
    for index, video in enumerate(sorted_videos):
      # assume the video is not new
      video_is_new = False

      # if latest_timestamp is false, the channel is new and so is the video
      # if the current video has a newer timestamp, it's obviously newer 
      if not latest_timestamp or (video['published_at'] > latest_timestamp):
        video_is_new = True
      
      # if the video is new and we didn't reach the limit
      if video_is_new and (index < insert_limit):
        status = "waiting"
      else:
        status = "skipped"
      
      # prepare variables
      video_id = video['video_id']
      channel_id = video['channel_id']
      author = video['author']
      title = video['title']
      published_at = video['published_at']

      # add each video to the list
      video_row = (video_id, channel_id, author, title, published_at, status)
      videos_to_insert.append(video_row)

    # add all rss videos to database
    with get_connection() as conn:
      conn.executemany(query, videos_to_insert)
      conn.commit()
      log(f"[DATABASE] Added videos from channel [{author}]")
  except sqlite3.Error as e:
    log(f"[DATABASE] Error trying to insert videos in the database: {e}")

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
    log(f"[DATABASE] Error trying to fetch video waitlist: {e}")
    # returns an empty list
    return []

# saves a video that was processed manually
# -----------------------------------------------------------------------------
def save_manual_video(video: dict):
  # do nothing without a video
  if not video:
    return

  # prepare variables
  video_id = video["video_id"]
  channel_id = video["channel_id"]
  author = video["author"]
  title = video["title"]
  published_at = video["published_at"]

  # using insert or replace here
  # so that if a video is marked as skipped or waiting,
  # it get processed and updated in the database
  query="""
    INSERT OR REPLACE INTO videos
    (video_id, channel_id, author, title, published_at, status)
    VALUES (?, ?, ?, ?, ?, 'processed');
  """

  try:
    with get_connection() as conn:
      # execute query
      conn.execute(query, (video_id, channel_id, author, title, published_at))
      # save changes
      conn.commit()
      log(f"[DATABASE] Manually processed video [{video_id}] from [{author}]")
  except sqlite3.Error as e:
    log(f"[DATABASE] Error trying to manually process video [{video_id}]")

# updates the status of a video after processing
# -----------------------------------------------------------------------------
def update_video_status(video_id: str, new_status: str):
  # do nothing without a video ID
  if not video_id:
    return

  # updates a single video status
  query = "UPDATE videos SET status = ? WHERE video_id = ?;"

  try:
    with get_connection() as conn:
      # execute query
      conn.execute(query, (new_status, video_id))
      # save changes
      conn.commit()
  except sqlite3.Error as e:
    log(f"[DATABASE] Error trying to update video [{video_id} status]")

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
        log("[DATABASE] Database empty")
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
          # use a more readable date
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
    log(f"[DATABASE] Error trying to print database: {e}")

# -----------------------------------------------------------------------------
if __name__ == "__main__":
  print_database()

