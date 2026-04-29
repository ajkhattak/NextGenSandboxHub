import json
from pathlib import Path
import requests
import os
import shutil
import zipfile


sandbox_dir = os.environ.get("SANDBOX_DIR")

def download_from_s3(out_path, s3_url):
    print(f"Downloading file: {s3_url}")

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
    s3_bucket  = "communityhydrofabric"
    s3_region  = "us-east-1"
    s3_key = "hydrofabrics/community/resources/dhbv_attrs.parquet"
    url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"

    output_dir = Path(f"{sandbox_dir}/extern/dhbv2/ngen_resources/data/dhbv_2_mts/model/dhbv_2_mts/")
    
    local_file = Path(output_dir) / "dhbv_attrs.parquet"
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


def download_mts_model():
    # dHBV trained weights
    s3_bucket  = "mhpi-spatial"
    s3_region  = "us-east-2"
    s3_key = "mhpi-release/models/owp/dhbv_2_mts.zip"
    MODEL_URL = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"
    
    zip_path = Path("/tmp/dhbv_2_mts.zip")
    temp_dir = Path("/tmp/dhbv_2_mts")
    model_dir = Path(f"{sandbox_dir}/extern/dhbv2/ngen_resources/data/dhbv_2_mts/model/dhbv_2_mts/")

    # Skip if already exists
    if model_dir.exists() and any(model_dir.iterdir()):
        print("Model already exists. Skipping.")
        return

    temp_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    if not download_from_s3(zip_path, MODEL_URL):
        raise RuntimeError("Download failed")

    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(temp_dir)

    # Move weights to the desired location
    src = temp_dir / "dhbv_2_mts"

    for item in src.iterdir():
        dest = model_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    zip_path.unlink(missing_ok=True)

    print("MTS model ready.")

if __name__ == "__main__":

    download_mts_model()

    download_dhbv_attributes()
