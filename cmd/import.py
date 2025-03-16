import json
import os
import requests
import sys
from dotenv import load_dotenv

BASE_URL = "http://localhost:8080"
EXTRA_PARAMS = ""


def load_sources(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def load_content(source_path, source_dir):
    # If source_path is an absolute path, use it without modifications.
    if os.path.isabs(source_path):
        full_path = source_path
    else:
        # Otherwise, load it relative to the directory containing sources.json (assumed to be the script's directory)
        full_path = os.path.join(source_dir, source_path)
    if not os.path.exists(full_path):
        # File does not exist, skip without printing an error.
        return None
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {full_path}: {e}")
        return None


def get_nonexistent_sources(sources):
    names = [s["name"] for s in sources]
    url = f"{BASE_URL}/sources/exists?{EXTRA_PARAMS}"
    try:
        resp = requests.request("GET", url, json=names, headers={
                                "accept": "application/json", "Content-Type": "application/json"})
        if resp.status_code == 200:
            existing: list[bool] = resp.json()
            return [s for s, e in zip(sources, existing) if not e]
        else:
            print(
                f"Failed to check existence. Server responded with: {resp.status_code}")
    except Exception as e:
        print(f"Error calling {url}: {e}")
        print("Assuming no sources exist.")
    return sources


def upload_sources_batch(sources, source_dir):
    """
    Uploads a batch of source files to a remote server.

    This function takes a list of source dictionaries, where each dictionary must
    contain at least the keys "name" and "path". For each source, it loads the file content
    (using the load_content function provided elsewhere) and constructs a payload that is then
    sent to the designated upload URL (constructed using the global BASE_URL).

    If the upload attempt returns a status code of 200, the function prints a success message
    indicating the number of sources uploaded. Otherwise, if the upload fails and there is only one
    source in the input list, it prints an error message with details from the server response.
    In cases where the batch has more than one source and the upload fails, the list is split in half
    and the function recursively attempts to upload each half separately.

    Parameters:
        sources (list of dict): A list of source dictionaries, each containing:
            - "name" (str): A unique name or identifier for the source.
            - "path" (str): The file path to load the source content.

    Returns:
        None
    """
    if not sources:
        return

    payload = []

    for s in sources:
        content = load_content(s["path"], source_dir)
        if content is None:
            pre = s["name"][:10].replace("\n", "/n")
            suf = s["name"][-30:].replace("\n", "/n")
            print(f"Skipping source '{pre}...{suf}' because file not found.")
            continue
        payload.append({
            "source_name": s["name"],
            "content": content
        })

    try:
        resp = requests.put(f"{BASE_URL}/sources/upload?{EXTRA_PARAMS}", json=payload,
                            headers={
                                "accept": "application/json",
                                "Content-Type": "application/json",
                                "X-API-Key": os.environ.get("IMPORT__API_KEY")
                            })
    except Exception as e:
        print(f"Error uploading sources: {e}")
        return

    if resp.status_code == 200:
        print(f"Uploaded {len(payload)} source(s) successfully.")
    elif resp.status_code == 403:
        print("Access denied. Please check your API key.")
    elif resp.status_code == 500 or resp.status_code == 400:
        # If there is only one source, print the error message.
        if len(sources) == 1:
            print(
                f"Failed to upload source '{sources[0]['name']}'. Status code: {resp.status_code}. Response: {resp.text}")
        else:
            # Split the list into two parts and try each one.
            mid = len(sources) // 2
            print(
                f"Batch upload failed ({resp.status_code}). Splitting into two batches: 0-{mid-1} and {mid}-{len(sources)-1}")
            upload_sources_batch(sources[:mid], source_dir)
            upload_sources_batch(sources[mid:], source_dir)
    else:
        print(
            f"Failed to upload sources. Status code: {resp.status_code}. Response: {resp.text}")


def main():
    if len(sys.argv) > 1:
        sources_file = sys.argv[1]
    else:
        sources_file = os.path.join(os.path.dirname(__file__), "sources.json")

    try:
        sources = load_sources(sources_file)
    except Exception as e:
        print(f"Failed to load sources from {sources_file}: {e}")
        return

    sources_to_upload = get_nonexistent_sources(sources)
    if not sources_to_upload:
        print("No new sources to upload.")
        return

    print(f"{len(sources_to_upload)} source(s) need to be uploaded.")
    source_dir = os.path.dirname(sources_file)
    upload_sources_batch(sources_to_upload, source_dir)


if __name__ == "__main__":
    load_dotenv()
    BASE_URL = os.environ.get("IMPORT__BASE_URL", "http://localhost:8080")
    EXTRA_PARAMS = os.environ.get("IMPORT__EXTRA_PARAMS", "")
    main()
