import os
import time
import httpx
import subprocess

# External service URL
VALIDATION_URL = "http://localhost:4010/"
CHANGED_FILES = os.getenv("CHANGED_FILES", "")
changed_files = []
network_name = "skgif_network"

if CHANGED_FILES and CHANGED_FILES != "":
    changed_files: list = CHANGED_FILES.split()

print(f"CHANGED_FILES: {CHANGED_FILES}")


def get_pushed_files():
    return [f"./{file}" for file in changed_files if file.endswith(".json")]


def validate_file(file_path):
    """Validate a single file against the external service."""
    print(f"Validating {file_path}...")
    filename = os.path.basename(file_path)
    url_part = file_path.split("/")[-2]  # Get the folder name, which is the url part
    # TODO: update the URL and path, this should take the jsons from parent directory
    url = VALIDATION_URL + "products/" + filename
    url = VALIDATION_URL + f"{url_part}/" + filename
    print(f"Validation URL: {url}")
    response = httpx.get(url)
    print(f"Response: {response.status_code} {response.text}")
    if 200 <= response.status_code < 303:
        print(f"✅ {file_path} is valid.")
        return True
    else:
        print(f"❌ {file_path} is invalid.")
        return False


def create_docker_network(network_name: str):
    """Create a Docker network if it doesn't already exist."""
    try:
        subprocess.run(
            ["docker", "network", "inspect", network_name],
            check=True, text=True, capture_output=True
        )
        print(f"Docker network '{network_name}' already exists.")
    except subprocess.CalledProcessError:
        print(f"Creating Docker network '{network_name}'...")
        subprocess.run(
            ["docker", "network", "create", network_name],
            check=True, text=True
        )
        print(f"Docker network '{network_name}' created.")


def start_prism_container(spec_path: str):
    docker_command = [
        "docker", "run", "--rm",
        "--name", "prism",
        "--hostname", "prism",
        "--network", network_name,
        "--platform", "linux/amd64",
        "--init",
        "-v", f"{spec_path}:/tmp/skg-if-api.yaml",
        "-p", "4010:4010",
        "stoplight/prism:4",
        "proxy", "-h", "0.0.0.0", "/tmp/skg-if-api.yaml", "http://fastapi:8000", "--errors"
    ]
    subprocess.Popen(docker_command)


def start_fastapi_container(data_path: str):
    docker_command = [
        "docker", "run", "--rm",
        "--name", "fastapi",
        "--hostname", "fastapi",
        "--network", network_name,
        "-v", f"{data_path}:/app/data",
        "-v", "./openapi/docker_build/app.py:/app/app.py",
        "-p", "8000:8000",
        "vicding81/athenstest:latest",
        "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"
    ]
    subprocess.Popen(docker_command)


def stop_docker_container(container_name: str):
    """Stop a Docker container if it is running."""
    try:
        subprocess.run(
            ["docker", "stop", container_name],
            check=True, text=True
        )
        print(f"Docker container '{container_name}' stopped successfully.")
    except subprocess.CalledProcessError:
        print(f"Docker container '{container_name}' could not be stopped or does not exist.")


def is_container_running(container_name: str, retry_interval: int = 10, retries: int = 5) -> bool:
    """Ensure the specified Docker container is running."""
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
                check=True, text=True, capture_output=True
            )
            if result.stdout.strip() == "true":
                print(f"Container '{container_name}' is already running.")
                return True
            else:
                print(f"Container '{container_name}' is not running. Attempt {attempt + 1}/{retries}")
        except subprocess.CalledProcessError:
            print(f"Container '{container_name}' does not exist or is not running. Attempt {attempt + 1}/{retries}")

        if attempt < retries - 1:
            time.sleep(retry_interval)

    print(f"Failed to ensure container '{container_name}' is running after {retries} attempts.")
    return False


def main():
    """Main function to validate pushed files."""
    print(f"CHANGED_FILES: {CHANGED_FILES}")
    pushed_files = get_pushed_files()
    # pushed_files = ["./openapi/ver/current/sample_data/products/test1.json", "./openapi/ver/test/sample_data/products/test.json"]
    print(f"Pushed files: {pushed_files}")
    if not pushed_files:
        print("No JSON files to validate.")
        return

    # Create Docker network if it doesn't exist
    create_docker_network(network_name)

    all_valid = True
    for file_path in pushed_files:
        if os.path.exists(file_path):
            # setup environment: 1. fetch skgif spec 2. start corresponding docker container
            # get skgif spec
            spec_path = file_path.split("/")[:-3]
            spec_path = "/".join(spec_path) + "/skg-if-openapi.yaml"
            # get data path for fastapi container
            fastapi_data_path = file_path.split("/")[:-2]
            fastapi_data_path = "/".join(fastapi_data_path)
            print(f"FastAPI data path: {fastapi_data_path}, Spec path: {spec_path}")

            if not os.path.exists(spec_path):
                print(f"Spec file {spec_path} does not exist.")
                all_valid = False
                continue
            print(f"Spec file path: {spec_path}")
            # start docker container
            start_fastapi_container(fastapi_data_path)
            if not is_container_running("fastapi"):
                print("FastAPI container is not running. Exiting.")
                exit(1)
            start_prism_container(spec_path)
            if not is_container_running("prism"):
                print("Prism container is not running. Exiting.")
                exit(1)

            if not validate_file(file_path):
                all_valid = False
            stop_docker_container("prism")
            stop_docker_container("fastapi")
        else:
            print(f"⚠️ File {file_path} does not exist locally.")
            all_valid = False

    if not all_valid:
        exit(1)


if __name__ == "__main__":
    main()
