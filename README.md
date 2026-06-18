# yt-idea-bot

Automated tool that monitors YouTube channels via RSS, saves new videos metadata, waits 48 hours, extracts the content ideas from the comments using Gemini and sends them to Discord.

---

## Project files

* **`listener.py`**: Gets new videos from the YouTube RSS feed and saves them to the database.
* **`fetcher.py`**: Fetches comments for expired videos, processes them with Gemini, and sends the results to Discord.
* **`database.py`**: Manages the SQLite database.
* **`channels.json.example`**: Example file for the channel list that will be monitored.
* **`.env.example`**: Example file for the environment variables needed.
* **`pyproject.toml`**: Python project configuration and dependencies.
* **`cron.template`**: Automation template for cron.
---

## Setup

Install `uv`:
```bash
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

Install python dependencies:

```bash
uv sync
```

## Configuration

### 1. Environment Variables

```bash
cp .env.example .env
```

Open `.env` and enter your `YOUTUBE_API_KEY`, `GEMINI_API_KEY`, and `DISCORD_WEBHOOK_URL`. It won't work without them.

### 2. Channels list

```bash
cp channels.json.example channels.json
```

Open `channels.json` and add the ID and name of the channels you want to monitor. 

### 3. Listener
In `save_rss_videos()` you can set a different limit of videos to process at once (default is 3). This means that no matter how many videos are in the wait list, only 3 will be processed per channel per batch, leaving the rest for the next cycle.

### 4. Fetcher
In `get_expired_videos()` you can change the amount of time it waits to fetch the comments (default is 48h).

It's not unusual to get status `500` when trying to call the Gemini API. It uses the free tier, so it has high demand, limits and low priority. Servers can also be overloaded. 

There is a fallback strategy to avoid videos piling up in the database due to constant status `500` errors. It first tries to use the dense `gemma4` model. If it fails, it tries the MoE version. If it fails again, then the `gemini 3.1 flash lite` model is used.

In summary:
```
gemma-4-31b-it -> gemma-4-26b-a4b-it -> gemini-3.1-flash-lite
```

This way we can take advantage of the generous quota from both of the `gemma4` models first and if they fail, we use the quota from `gemini 3.1 flash lite`, which is smaller, but less prone to have status `500` errors.

Videos that fail all three attempts to be processed will remain with the `WAITING` status and will be processed in the next cycle.

## Database

The pipeline automatically creates an SQLite database named `yt-pipeline.db`. To completely erase the database, just delete this file from the directory.

If you want to check the contents of the database, run:
```bash
uv run database.py
```

## Automation (Cron)
To install the automated schedule into your system `crontab`, run this command from the project root:

**IT MUST BE FROM THE PROJECT FOLDER WHERE THE `.py` FILES ARE, OTHERWISE IT WON'T WORK**

```bash
sed "s|TARGET_DIRECTORY|$PWD|g" cron.template | crontab -
```
This will configure it run `listener.py` every 2h on the odd hours (01, 03, 05...) and run `fetcher.py` every 2h on the even hours (02, 04, 06...).

This means that every 2h it will get the new videos released in the RSS feed and every 2h it will try to analyze the contents and send it to Discord (for expired videos).

Example:
```
├── 01:00 - listener
├── 02:00 - fetcher
├── 03:00 - listener
├── 04:00 - fetcher
├── 05:00 - listener
├── 06:00 - fetcher
...
```

A `pipeline.log` file will be created with the last 1000 entries of the log. You can check it for errors.

## Manual Run
To force the analysis of a specific video immediately, run:

```bash
uv run fetcher.py --url "YOUTUBE_URL"
```
This is useful for old videos or channels that you don't want to add in the monitoring list.
When using manual run, you can check the logs in the terminal.

## License
MIT
