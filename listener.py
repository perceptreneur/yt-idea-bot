# package imports
import feedparser
import json

# local imports
import database
from utils import log

# create datyabase and table (if it doesnt exists)
database.init_db()

# channel list file
channel_list = "channels.json"
# rss feed base url
rss_base = "https://www.youtube.com/feeds/videos.xml?"

# uses the correct parameter in the feed url
# -----------------------------------------------------------------------------
def get_feed_parameter(channel_id: str) -> str:
  # if it starts with UC it's the channel ID
  if channel_id[:2] == "UC":
    return "channel_id"

  # anything else is the playlist ID
  return "playlist_id"

# -----------------------------------------------------------------------------
def main():
  # opens channel list for parsing
  with open(channel_list, 'r') as f:
    channels = json.load(f)

  # goes through each channel in the list
  for channel_id, config in channels.items():
    # get channel name
    channel = config['channel_name']
    log(f"[LISTENER] Starting parse for channel [{channel}]")

    # get the correct url parameter
    param = get_feed_parameter(channel_id)

    # get rss feed for this channel ID
    feed_data = feedparser.parse(rss_base + param + "=" + channel_id)

    # if the feed is empty for some reason
    # ignore it and go to the next channel
    if not feed_data:
      log(f"[LISTENER] Error: Couldn't get RSS data for channel [{channel}]")
      continue

    # get channel name from rss feed
    channel_name = getattr(getattr(feed_data, "feed", None), "author", "Unknown")
    # start with empty list of videos
    video_list = []

    # go through each video in the rss feed
    for video in feed_data.entries:
      # relevant video info:
      #
      # yt_channelid  -> channel ID
      # yt_videoid    -> video ID
      # links[0],href -> video link
      # author        -> author (channel name)
      # title         -> title
      # published     -> published date/time

      # ignore all shorts
      if "shorts" in video.links[0].href:
        continue

      # prepare data to database
      video_list.append({
        "video_id": video.yt_videoid,
        "channel_id": video.yt_channelid,
        "author": video.author,
        "title": video.title,
        "published_at": video.published,
      })

    # save new videos to database
    database.save_rss_videos(video_list, channel_name)

# -----------------------------------------------------------------------------
if __name__ == "__main__":
  main()
