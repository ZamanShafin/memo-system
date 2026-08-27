import os
import zipfile

def package_source_zip():
    output_filename = "source_code.zip"
    exclude_dirs = {".venv", "__pycache__", ".pytest_cache", ".git", "uploads"}
    exclude_files = {"memo_system.db", "memo_system.db-shm", "memo_system.db-wal", "source_code.zip"}

    print(f"Creating source code package: {output_filename}...")
    
    with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("."):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
            
            for file in files:
                if file in exclude_files or file.endswith(".pyc"):
                    continue
                    
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, ".")
                zipf.write(file_path, rel_path)
                print(f"  + Added {rel_path}")

    size_kb = os.path.getsize(output_filename) / 1024
    print(f"\n[SUCCESS] Source code ZIP successfully created: {output_filename} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    package_source_zip()
