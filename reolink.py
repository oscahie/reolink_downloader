import requests
import json
import os
from datetime import datetime
import urllib3
import argparse
import time

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_token(camera_ip, username, password, port=443):
    """Get authentication token from the camera"""
    url = f"https://{camera_ip}:{port}/api.cgi?cmd=Login"
    headers = {'Content-Type': 'application/json'}

    data = [{
        "cmd": "Login",
        "param": {
            "User": {
                "Version": "0",
                "userName": username,
                "password": password
            }
        }
    }]

    response = requests.post(url, headers=headers, json=data, verify=False)
    if response.status_code == 200:
        result = response.json()
        if result[0]["code"] == 0 and "value" in result[0]:
            token = result[0]["value"]["Token"]["name"]
            print(f"Successfully authenticated. Token: {token}")
            return token
    print(f"Authentication failed: {response.text}")
    return None

def search_recordings(camera_ip, token, channel, start_time, end_time, port=443):
    """Search for recordings using the Search API"""
    url = f"https://{camera_ip}:{port}/api.cgi?cmd=Search&token={token}"
    headers = {'Content-Type': 'application/json'}

    data = [{
        "cmd": "Search",
        "action": 0,
        "param": {
            "Search": {
                "channel": channel,
                "onlyStatus": 0,
                "streamType": "main",
                "StartTime": {
                    "year": int(start_time[0:4]),
                    "mon": int(start_time[4:6]),
                    "day": int(start_time[6:8]),
                    "hour": int(start_time[8:10]),
                    "min": int(start_time[10:12]),
                    "sec": int(start_time[12:14])
                },
                "EndTime": {
                    "year": int(end_time[0:4]),
                    "mon": int(end_time[4:6]),
                    "day": int(end_time[6:8]),
                    "hour": int(end_time[8:10]),
                    "min": int(end_time[10:12]),
                    "sec": int(end_time[12:14])
                }
            }
        }
    }]

    response = requests.post(url, headers=headers, json=data, verify=False)

    if response.status_code == 200:
        result = response.json()
        if result[0]["code"] == 0 and "value" in result[0]:
            if "SearchResult" in result[0]["value"] and "File" in result[0]["value"]["SearchResult"]:
                return result[0]["value"]["SearchResult"]["File"]

    return []

def download_recording(camera_ip, token, filename, output_path, port=443):
    """Download a recording using direct URL with token"""
    # Create the download URL as specified in the query
    source = filename
    output = os.path.basename(filename)
    url = f"https://{camera_ip}:{port}/cgi-bin/api.cgi?cmd=Download&source={source}&output={output}&token={token}"

    print(f"Downloading {output} using URL: {url}")

    try:
        with requests.get(url, verify=False, stream=True) as response:
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                print(f"File size: {total_size / (1024 * 1024):.2f} MB")

                with open(output_path, 'wb') as f:
                    downloaded = 0
                    last_percent = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            percent = int((downloaded / total_size) * 100)
                            if percent >= last_percent + 10:
                                print(f"Progress: {percent}%")
                                last_percent = percent

                print(f"Successfully downloaded {output_path}")
                return True
            else:
                print(f"Download failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
    except Exception as e:
        print(f"Error during download: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Download Reolink camera recordings within a time range.')
    parser.add_argument('--ip', required=True, help='Camera IP address')
    parser.add_argument('--username', required=True, help='Camera username')
    parser.add_argument('--password', required=True, help='Camera password')
    parser.add_argument('--port', type=int, default=443, help='Camera port (default: 443)')
    parser.add_argument('--start', required=True, help='Start date/time (format: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', required=True, help='End date/time (format: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--output', default='./recordings', help='Output directory (default: ./recordings)')
    parser.add_argument('--channel', type=int, default=0, help='Camera channel (default: 0)')
    parser.add_argument('--list-only', action='store_true', help='Only list recordings, do not download')

    args = parser.parse_args()

    # Parse date strings
    start_dt = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")

    start_time = start_dt.strftime("%Y%m%d%H%M%S")
    end_time = end_dt.strftime("%Y%m%d%H%M%S")

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Get authentication token
    token = get_token(args.ip, args.username, args.password, args.port)
    if not token:
        print("Failed to authenticate with camera")
        return

    # Search for recordings
    recordings = search_recordings(args.ip, token, args.channel, start_time, end_time, args.port)

    if not recordings:
        print("No recordings found")
        return

    print(f"Found {len(recordings)} recordings")

    # Display recordings
    print("\n===== RECORDINGS FOUND =====")
    for i, rec in enumerate(recordings):
        name = rec.get("name", "unknown")
        size_bytes = int(rec.get("size", 0))
        size_mb = size_bytes / (1024 * 1024)

        # Format the start and end times for better readability
        if "StartTime" in rec and "EndTime" in rec:
            st = rec["StartTime"]
            et = rec["EndTime"]
            start_str = f"{st['year']}-{st['mon']:02d}-{st['day']:02d} {st['hour']:02d}:{st['min']:02d}:{st['sec']:02d}"
            end_str = f"{et['year']}-{et['mon']:02d}-{et['day']:02d} {et['hour']:02d}:{et['min']:02d}:{et['sec']:02d}"
            print(f"{i+1}. {name} - Size: {size_mb:.2f}MB, Time: {start_str} to {end_str}")
        else:
            print(f"{i+1}. {name} - Size: {size_mb:.2f}MB")

    # Save recording info to JSON for reference
    with open(os.path.join(args.output, "recordings_info.json"), "w") as f:
        json.dump(recordings, f, indent=2)

    # Download recordings if not list-only mode
    if not args.list_only:
        print("\n===== DOWNLOADING RECORDINGS =====")
        success_count = 0

        for i, rec in enumerate(recordings):
            name = rec.get("name", "")
            if not name:
                print(f"Recording {i+1} has no filename, skipping")
                continue

            # Create output file path
            output_file = os.path.join(args.output, os.path.basename(name))

            print(f"\nDownloading recording {i+1}/{len(recordings)}: {name}")

            # Add delay between downloads to avoid overwhelming the camera
            if i > 0:
                time.sleep(1)

            success = download_recording(args.ip, token, name, output_file, args.port)

            if success:
                success_count += 1

        print(f"\nDownload complete. Successfully downloaded {success_count} of {len(recordings)} recordings.")

if __name__ == "__main__":
    main()


