import json
from pathlib import Path
import requests
import os

S3_BUCKET  = "communityhydrofabric"
S3_REGION  = "us-east-1"
OUTPUT_DIR = "/Users/ahmadjankhattak/Core/input_data/dhbv_attributesX/"

def download_from_s3(out_path, s3_url):
    print("Downloading file...")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)


    try:
        with requests.get(s3_url, stream=True) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

    
def download_dhbv_attributes():
    s3_key = "hydrofabrics/community/resources/dhbv_attrs.parquet"
    url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
    
    local_file = Path(OUTPUT_DIR) / "dhbv_attrs.parquet"
    log_path = local_file.with_suffix(".log")

    # Fetch remote headers
    try:
        r = requests.head(url, timeout=10)
        r.raise_for_status()
        remote_headers = dict(r.headers)
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch headers: {e}")

    # Load local headers (if any)
    local_headers = {}
    if log_path.exists():
        try:
            with open(log_path) as f:
                local_headers = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Check if download is needed
    needs_download = (
        not local_file.exists()
        or remote_headers.get("ETag") != local_headers.get("ETag")
    )

    if needs_download:
        success = download_from_s3(out_path=local_file, s3_url=url)

        if success:
            with open(log_path, "w") as f:
                json.dump(remote_headers, f)
    else:
        print("File is up-to-date.")
        return


if __name__ == "__main__":
    download_dhbv_attributes()
