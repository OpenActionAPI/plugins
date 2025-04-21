import os
from PIL import Image
import shutil
import logging
from pathlib import Path
from tqdm import tqdm


def process_images(input_dir, quality, palette_colors):
	total_files = 0
	modified_files = 0
	original_size = 0
	new_size = 0

	target_ext = ".png"
	max_size = (144, 144)

	# Create a temporary directory for processed images
	temp_dir = os.path.join(input_dir, "temp_processed")
	os.makedirs(temp_dir, exist_ok=True)

	# Get list of files to process (excluding directories)
	files_to_process = [
		f
		for f in os.listdir(input_dir)
		if os.path.isfile(os.path.join(input_dir, f)) and not f.startswith("temp_processed")
	]

	# Initialize progress bar
	progress_bar = tqdm(files_to_process, desc="Processing images", unit="file")

	for filename in progress_bar:
		filepath = os.path.join(input_dir, filename)
		progress_bar.set_postfix(file=filename[:15] + "..." if len(filename) > 15 else filename)

		try:
			with Image.open(filepath) as img:
				total_files += 1
				original_size += os.path.getsize(filepath)

				img.thumbnail(max_size, Image.LANCZOS)

				if img.mode == "RGB":
					img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=palette_colors)

				# Remove metadata
				img.info.pop("icc_profile", None)

				# Prepare new filename
				new_filename = Path(filename).stem + target_ext
				temp_filepath = os.path.join(temp_dir, new_filename)

				# Save with optimized settings
				save_kwargs = {"compress_level": 9 - int((quality / 100) * 9), "optimize": True}
				img.save(temp_filepath, "PNG", **save_kwargs)

				# Count as modified only if we actually created a new file
				modified_files += 1
				new_size += os.path.getsize(temp_filepath)

		except Exception as e:
			logging.warning(f"Could not process {filename}: {str(e)}")
			continue

	# Replace original files with processed ones
	if modified_files > 0:
		for filename in os.listdir(temp_dir):
			src = os.path.join(temp_dir, filename)
			dst = os.path.join(input_dir, filename)

			if os.path.exists(dst):
				os.remove(dst)
			shutil.move(src, dst)

	# Clean up temporary directory
	shutil.rmtree(temp_dir)

	return total_files, modified_files, original_size, new_size


def main():
	input_dir = "./icons"
	if not os.path.exists(input_dir):
		print(f"Error: Directory '{input_dir}' does not exist.")
		return

	total_files, modified_files, original_size, new_size = process_images(
		input_dir=input_dir, quality=99, palette_colors=256
	)

	# Print results
	print("\nProcessing complete.")
	print(f"Total files processed: {total_files}")
	print(f"Files modified: {modified_files}")

	if modified_files > 0:
		size_change = original_size - new_size
		if size_change > 0:
			print(f"Space saved: {size_change / 1024:.2f} KB ({size_change} bytes)")
		elif size_change < 0:
			print(f"Space increased: {-size_change / 1024:.2f} KB ({-size_change} bytes)")
		else:
			print("No change in total storage space")


if __name__ == "__main__":
	main()
