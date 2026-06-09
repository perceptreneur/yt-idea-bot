# package imports
import feedparser
import json

# local imports
import database

# create datyabase and table (if it doesnt exists)
database.init_db()

# channel list file
channel_list = "channels.json"
# rss feed base url
rss_base = "https://www.youtube.com/feeds/videos.xml?channel_id="

def main():
  # opens channel list for parsing
  with open(channel_list, 'r') as f:
    channels = json.load(f)

  # goes through each channel in the list
  for channel_id, config in channels.items():
    print(f"Channel ID: {channel_id}")
    print(f"Name: {config['channel_name']}")
    print("-" * 30)

    # get rss feed for this channel ID
    d = feedparser.parse(rss_base + channel_id)
    # start with empty list of videos
    video_list = []

    # go through each video in the rss feed
    for video in d.entries:
      print(video.yt_channelid)
      print(video.yt_videoid)
      print(video.links[0].href)
      print(video.title)
      print(video.published)
      print("#" * 30)

      # prepare data to database
      video_list.append({
        "video_id": video.yt_videoid,
        "channel_id": video.yt_channelid,
        "title": video.title,
        "published_at": video.published,
      })

      # save new videos to database
      database.save_rss_videos(video_list)
      break

if __name__ == "__main__":
  main()
