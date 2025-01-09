import os


def combine_files(output_file='combined_file.txt', allowed_extensions=None, exclude_list=None):
    if allowed_extensions is None:
        allowed_extensions = {'.py', '.html', '.css', '.js'}

    if exclude_list is None:
        exclude_list = []

    # Convert exclude_list to absolute paths for accurate comparison
    exclude_abs_paths = [os.path.abspath(path) for path in exclude_list]

    # Get the current directory
    current_dir = os.getcwd()

    # Open the output file in write mode
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Walk through the directory tree
        for root, dirs, files in os.walk(current_dir):
            # Remove hidden directories from traversal
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            # Further exclude specified directories
            dirs[:] = [d for d in dirs if os.path.abspath(os.path.join(root, d)) not in exclude_abs_paths]

            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                file_path = os.path.join(root, file)
                abs_file_path = os.path.abspath(file_path)

                # Exclude files based on filename or their absolute path
                if (file_ext in allowed_extensions) and (file not in exclude_list) and (
                        abs_file_path not in exclude_abs_paths):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(f'===== {file_path} =====\n')
                            outfile.write(infile.read())
                            outfile.write('\n\n')  # Add spacing between files
                    except Exception as e:
                        print(f"Failed to read {file_path}: {e}")

    print(f"All specified files have been successfully combined into `{output_file}`.")


if __name__ == "__main__":
    # Example usage with exclusions
    exclusions = ['./ignore_dir', './quicktest.py', './static/ignore', './static/bootstrap.min.css']  # Add relative or absolute paths to exclude
    combine_files(exclude_list=exclusions)
