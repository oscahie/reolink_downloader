This is just a quick hack put together with the help of an LLM that can list and download all VOD recordings from a reolink camera that fall within a given time range. Reolink's local admin website and iOS app only allow downloading one file at a time, which quickly becomes a tedious process once you need to download more than a few minutes worth of video. 

Note: I'm not really planning of maintaining this, and it sure doesn't work perfectly but it's enough for my current needs and I reckon it might be useful to someone else too. Try running it again it if says auth error or doesn't list anything.

# Usage Example

```
python reolink_downloader.py --ip 192.168.1.238 --username admin --password yourpassword --start "2025-03-30 17:00:00" --end "2025-03-30 19:00:00" --output ./downloaded_videos
```
