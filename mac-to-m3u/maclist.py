import traceback
import requests
import json
from datetime import datetime
from urllib.parse import urlparse
import sys
import re
from typing import Dict, Tuple, Optional, Any, List
from tqdm import tqdm

def print_colored(text: str, color: str) -> None:
    """Prints colored text."""
    colors: Dict[str, str] = {
        "green": "\033[92m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
    }
    color_code: str = colors.get(color.lower(), "\033[0m")
    print(f"{color_code}{text}\033[0m")


def input_colored(prompt: str, color: str) -> str:
    """Gets user input with a colored prompt."""
    colors: Dict[str, str] = {
        "green": "\033[92m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
    }
    color_code: str = colors.get(color.lower(), "\033[0m")
    return input(f"{color_code}{prompt}\033[0m")


def get_base_url(base_url: str = "") -> str:
    parsed_url: str
    if base_url:
        parsed_url = urlparse(base_url.strip())
    else:
        """Gets base URL from user input and formats it correctly."""
        base_url_input: str = input_colored("Enter IPTV link: ", "cyan").strip()
        if not base_url_input:
            return ""
        parsed_url = urlparse(base_url_input)
        
    if parsed_url.hostname:
        scheme = parsed_url.scheme or "http"
        host = parsed_url.hostname
        port = parsed_url.port or 80
        return f"{scheme}://{host}:{port}"
    
    return ""

def get_mac_address(mac: str = "") -> str:
    if len(mac.strip()):
        return mac.strip().upper()
    
    """Gets MAC address from user input."""
    return input_colored("Input Mac address: ", "cyan").strip().upper()


def get_token(
    session: requests.Session, base_url: str, mac: str, timeout: int = 10
) -> Optional[str]:
    """Gets token using MAC authentication."""
    url = f"{base_url}/portal.php?action=handshake&type=stb&token=&JsHttpRequest=1-xml"

    headers = {"Authorization": f"MAC {mac}"}
    try:
        res = session.get(url, headers=headers, timeout=timeout)
        res.raise_for_status()
        data = res.json()
        return data["js"]["token"]
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        print_colored(f"Error fetching token: {e}", "red")
        
        if "res" in locals() and res and res.status_code != 403:
            print_colored(f"Server response: {res.status_code}, text: {res.text}", "yellow")
        return None
    except Exception as ex:
        print_colored(f"Error fetching token: Exception: {ex}", "red")
        if "res" in locals() and res and res.status_code != 403:
            print_colored(f"Server response: {res.text}", "yellow")
        return None


def get_subscription(
    session: requests.Session, base_url: str, token: str, timeout: int = 10
) -> bool:
    """Gets subscription information using a Bearer token."""
    url = f"{base_url}/portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"

    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = session.get(url, headers=headers, timeout=timeout)
        
        res.raise_for_status()
        data = res.json()
        mac = data["js"]["mac"]

        expiry = data.get("js", {}).get("phone", "N/A")
        print_colored(f"MAC = {mac}\nExpiry = {expiry}", "green")
        return True
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        print_colored(f"Error fetching subscription info: {e}", "red")
        if "res" in locals() and res and res.status_code != 403:
            print_colored(f"Server response: {res.status_code}, text: {res.text}", "yellow")
        return False
    except Exception as ex:
        print_colored(f"Error fetching subscription info: {ex}", "red")
        if "res" in locals() and res and res.status_code != 403:
            print_colored(f"Server response: {res.text}", "yellow")
        return False


def get_channel_list(
    session: requests.Session, base_url: str, token: str, timeout: int = 10
) -> Tuple[Optional[List[Dict]], Optional[Dict]]:
    """Gets the full channel list and genre information."""

    headers = {"Authorization": f"Bearer {token}"}
    try:

        url_genre = (
            f"{base_url}/server/load.php?type=itv&action=get_genres&JsHttpRequest=1-xml"
        )
        res_genre = session.get(url_genre, headers=headers, timeout=timeout)
        res_genre.raise_for_status()
        genre_data = res_genre.json()["js"]
        
        group_info = {group["id"]: group["title"] for group in genre_data}
 
        # url_channels = f"{base_url}/server/load.php?type=itv&action=get_all_channels&JsHttpRequest=1-json"
        url_channels = f"{base_url}/portal.php?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        res_channels = session.get(url_channels, headers=headers, timeout=timeout)
        res_channels.raise_for_status()
        if res_channels.json()["js"]:
            channels_data = res_channels.json()["js"]["data"]
            return channels_data, group_info
        else:
            print_colored(f"Channel list is empty. Maybe you have no subscription or expired?", "magenta")
            return None, None

    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        print_colored(f"Error fetching channel list: {e}", "red")
        print_colored(f"RequestException. Server response: {group_info}", "yellow")
        
        return None, None
    except Exception as ex:
        print_colored(f"Error fetching subscription info: {ex}", "red")
        print_colored(f"Exception. Server response: {res_channels.text}", "yellow")
        return None, None

def save_channel_list(
    base_url: str, channels_data: List[Dict], group_info: Dict, mac: str
) -> None:
    """Saves the channel list to an M3U file."""
    sanitized_url = re.sub(r"[\W_]+", "-", base_url)
    filename = f'{sanitized_url}_{mac.replace(":", "-")}_{datetime.now().strftime("%Y-%m-%d")}.m3u'
    count = 0
    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write("#EXTM3U\n")
            for channel in channels_data:
                group_id = channel.get("tv_genre_id", "0")
                group_name = group_info.get(group_id, "General")
                name = channel.get("name", "Unknown Channel")
                logo = channel.get("logo", "")

                cmd_url_raw = channel.get("cmds", [{}])[0].get("url", "")
                cmd_url = cmd_url_raw.replace("ffmpeg ", "")
                if "localhost" in cmd_url:
                    ch_id_match = re.search(r"/ch/(\d+)", cmd_url)
                    if ch_id_match:
                        ch_id = ch_id_match.group(1)
                        cmd_url = f"{base_url}/play/live.php?mac={mac}&stream={ch_id}&extension=ts"

                if not cmd_url:
                    continue

                file.write(
                    f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_name}",{name}\n'
                )
                file.write(f"{cmd_url}\n")
                count += 1
        print_colored(f"\nTotal channels found: {count}", "green")
        print_colored(f"Channel list saved to: {filename}", "blue")
    except IOError as e:
        print_colored(f"Error saving channel list file: {e}", "red")


def main() -> None:
    """Main function to orchestrate the process."""
    try:
        print_colored(f"Starting the process... {sys.argv}", "blue")
        base_url: str
        mac: str
        if len(sys.argv) >= 2:
            base_url = get_base_url(sys.argv[1])
            if (sys.argv[2] == "|"):
                mac = get_mac_address(sys.argv[3])
            else:
                mac = get_mac_address(sys.argv[2])
        else:
            base_url = get_base_url()
            mac = get_mac_address()

        print_colored(f"URL = {base_url}", "yellow")
        print_colored(f"MAC = {mac}", "yellow")

        
        if not base_url:
            print_colored("\nExiting..., URL is empty", "yellow")
            sys.exit(1)
        
        if not mac:
            print_colored("\nExiting..., MAC is empty", "yellow")
            sys.exit(2)
        
        session = requests.Session()
        session.cookies.update({"mac": mac})
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",               
                "Referer": f"{base_url}/c/",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        token = get_token(session, base_url, mac)
        if token:
            print_colored("Token acquired successfully.", "green")
            if get_subscription(session, base_url, token):
                print_colored("Fetching channel list...", "cyan")
                channels_data, group_info = get_channel_list(session, base_url, token)
                if channels_data and group_info:
                    save_channel_list(base_url, channels_data, group_info, mac)
    except KeyboardInterrupt:
        print_colored("\nExiting gracefully...", "yellow")
        sys.exit(0)
    except Exception as e:
        # error_str = traceback.format_exc()
        print_colored(f"An unexpected error occurred in main: {e}", "red")
        # print_colored(f"An unexpected error occurred in main: {error_str}", "red")


if __name__ == "__main__":
    main()
