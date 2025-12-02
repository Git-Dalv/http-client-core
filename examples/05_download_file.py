"""
File Download Examples

Demonstrates downloading files with progress tracking and streaming.
"""

from src.http_client import (
    HTTPClient,
    HTTPClientConfig,
    SecurityConfig,
    ResponseTooLargeError,
)
import os
import tempfile


def basic_download():
    """Basic file download."""
    print("\n=== Basic Download ===")

    client = HTTPClient(base_url="https://httpbin.org")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "downloaded_file.json")

        print("Downloading /json...")
        bytes_downloaded = client.download("/json", output_path)

        print(f"Downloaded: {bytes_downloaded} bytes")
        print(f"Saved to: {output_path}")

        # Verify file
        if os.path.exists(output_path):
            with open(output_path, 'rb') as f:
                content = f.read()
                print(f"File size: {len(content)} bytes")


def download_with_progress():
    """Download with progress bar (requires tqdm)."""
    print("\n=== Download with Progress ===")

    try:
        import tqdm
        has_tqdm = True
    except ImportError:
        has_tqdm = False
        print("Note: Install tqdm for progress bars: pip install tqdm")

    client = HTTPClient(base_url="https://httpbin.org")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "image.jpeg")

        print("Downloading /image/jpeg...")
        bytes_downloaded = client.download(
            "/image/jpeg",
            output_path,
            show_progress=has_tqdm  # Show progress if tqdm available
        )

        print(f"\nDownloaded: {bytes_downloaded} bytes")


def download_with_size_limit():
    """Download with size limit protection."""
    print("\n=== Download with Size Limit ===")

    # Set small size limit for demonstration
    security_cfg = SecurityConfig(
        max_response_size=1024  # Only 1KB allowed
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        security=security_cfg
    )

    client = HTTPClient(config=config)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "large_file.json")

        print("Trying to download large file with 1KB limit...")
        try:
            client.download("/json", output_path)
            print("Download succeeded")
        except ResponseTooLargeError as e:
            print(f"Download blocked: {e}")
            print("✓ Size limit protection works!")


def download_custom_chunk_size():
    """Download with custom chunk size."""
    print("\n=== Custom Chunk Size ===")

    client = HTTPClient(base_url="https://httpbin.org")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "data.json")

        print("Downloading with 4KB chunks...")
        bytes_downloaded = client.download(
            "/json",
            output_path,
            chunk_size=4096  # 4KB chunks (default is 8KB)
        )

        print(f"Downloaded: {bytes_downloaded} bytes")
        print(f"Chunk size: 4096 bytes")


def download_multiple_files():
    """Download multiple files."""
    print("\n=== Download Multiple Files ===")

    client = HTTPClient(base_url="https://httpbin.org")

    files_to_download = [
        ("/json", "file1.json"),
        ("/xml", "file2.xml"),
        ("/html", "file3.html"),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        print("Downloading multiple files...")

        total_bytes = 0
        for endpoint, filename in files_to_download:
            output_path = os.path.join(tmpdir, filename)

            try:
                bytes_downloaded = client.download(endpoint, output_path)
                total_bytes += bytes_downloaded
                print(f"  ✓ {filename}: {bytes_downloaded} bytes")
            except Exception as e:
                print(f"  ✗ {filename}: {e}")

        print(f"\nTotal downloaded: {total_bytes} bytes")
        print(f"Files in directory: {len(os.listdir(tmpdir))}")


def download_with_error_handling():
    """Download with comprehensive error handling."""
    print("\n=== Download with Error Handling ===")

    client = HTTPClient(base_url="https://httpbin.org")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test.dat")

        print("Attempting download...")
        try:
            bytes_downloaded = client.download("/status/404", output_path)
            print(f"Downloaded: {bytes_downloaded} bytes")

        except ResponseTooLargeError as e:
            print(f"File too large: {e}")

        except FileNotFoundError as e:
            print(f"File not found: {e}")

        except PermissionError as e:
            print(f"Permission denied: {e}")

        except Exception as e:
            print(f"Download failed: {type(e).__name__}: {e}")

        # Check if file was created
        if os.path.exists(output_path):
            print(f"File exists: {output_path}")
            # Cleanup happens automatically with tmpdir
        else:
            print("File was not created (expected for 404)")


def download_resume_simulation():
    """Simulate resumable download (partial content)."""
    print("\n=== Partial Download (Range Request) ===")

    client = HTTPClient(base_url="https://httpbin.org")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "partial.dat")

        print("Downloading first 100 bytes only...")

        # Use Range header to download only part of the file
        response = client.get(
            "/bytes/1000",  # Server has 1000 bytes
            headers={"Range": "bytes=0-99"}  # Request only first 100 bytes
        )

        # Save to file
        with open(output_path, 'wb') as f:
            f.write(response.content)

        file_size = os.path.getsize(output_path)
        print(f"Downloaded: {file_size} bytes")
        print(f"Status: {response.status_code} (206 = Partial Content)")


def streaming_response():
    """Process large response as stream without saving to file."""
    print("\n=== Streaming Response (No File) ===")

    client = HTTPClient(base_url="https://httpbin.org")

    print("Streaming response and processing chunks...")

    # For very large responses, you might want to process without download()
    # However, standard get() loads full response into memory
    # The download() method is specifically designed for streaming to disk

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "streamed.dat")

        # Download streams internally
        bytes_downloaded = client.download("/bytes/10000", output_path, chunk_size=1024)

        print(f"Streamed and saved: {bytes_downloaded} bytes")
        print("✓ Memory-efficient streaming complete")


if __name__ == "__main__":
    print("=" * 50)
    print("HTTP Client - File Download Examples")
    print("=" * 50)

    try:
        basic_download()
        download_with_progress()
        download_with_size_limit()
        download_custom_chunk_size()
        download_multiple_files()
        download_with_error_handling()
        download_resume_simulation()
        streaming_response()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Error: {e}")
