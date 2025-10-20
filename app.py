import sys
import requests

def fetch_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/129.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;"
                  "q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        # Optionally:
        # "Referer": "https://example.com/",
        # "Origin": "https://example.com",
        # "Sec‑Fetch‑Site": "none",
        # "Sec‑Fetch‑Mode": "navigate",
        # "Sec‑Fetch‑User": "?1",
        # "Sec‑Fetch‑Dest": "document",
    }

    session = requests.Session()
    response = session.get(url, headers=headers)
    print("Status:", response.status_code)
    if response.status_code == 200:
        print(response.text[:500])  # print first 500 chars of HTML
    else:
        print("Failed to fetch:", response.text)


def main():
    print("Enter musescore url (type 'exit' or Ctrl-C to quit).")
    while True:
        try:
            cmd = input(">>> ")  # prompt
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        
        cmd = cmd.strip()
        if cmd.lower() in ("exit", "quit"):
            break
        
        if not cmd:
            continue
        
        fetch_url(cmd)
        

if __name__ == "__main__":
    main()
