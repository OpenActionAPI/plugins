import os
import argparse
from PIL import Image
import shutil
import logging
from pathlib import Path
from tqdm import tqdm


def optimize_with_palette(image, use_palette, palette_colors=256):
	"""Convert to palette-based image if enabled and beneficial"""
	if not use_palette:
		return image

	# Only convert images that can benefit from palette
	if image.mode not in ["RGB", "RGBA", "L", "LA"]:
		return image

	# Create temporary files for comparison
	temp_original = Path("temp_original.png")
	temp_palette = Path("temp_palette.png")

	# Save original version
	image.save(temp_original, "PNG")
	original_size = temp_original.stat().st_size

	try:
		# Convert to palette mode
		palette_img = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=palette_colors)
		if image.mode == "RGBA":
			palette_img.putalpha(image.split()[-1])

		palette_img.save(temp_palette, "PNG")
		palette_size = temp_palette.stat().st_size

		# Use whichever is smaller
		if palette_size < original_size:
			return palette_img
	except Exception as e:
		logging.debug(f"Palette conversion failed: {e}")
	finally:
		# Clean up temp files
		if temp_original.exists():
			temp_original.unlink()
		if temp_palette.exists():
			temp_palette.unlink()

	return image


def process_images(
	input_dir,
	force_reformat,
	quality=99,
	use_palette=True,
	palette_colors=256,
):
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
				original_width, original_height = img.size
				needs_resize = original_width > max_size[0] or original_height > max_size[1]

				# Determine if we need to process this file
				needs_processing = force_reformat or needs_resize

				if not needs_processing:
					continue

				total_files += 1
				original_size += os.path.getsize(filepath)

				# Resize if needed
				if needs_resize:
					img.thumbnail(max_size, Image.LANCZOS)

				if use_palette:
					img = optimize_with_palette(img, use_palette, palette_colors)

				# Prepare new filename
				new_filename = Path(filename).stem + target_ext
				temp_filepath = os.path.join(temp_dir, new_filename)

				# Save with optimized settings
				save_kwargs = {"compress_level": 9 - int((quality / 100) * 9), "optimize": True}
				img.save(temp_filepath, "PNG", **save_kwargs)

				# Check if the new file is actually smaller (if not replacing due to force_reformat)
				if not force_reformat and os.path.exists(os.path.join(input_dir, new_filename)):
					existing_size = os.path.getsize(os.path.join(input_dir, new_filename))
					new_file_size = os.path.getsize(temp_filepath)
					if new_file_size >= existing_size:
						os.remove(temp_filepath)
						continue

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
	parser = argparse.ArgumentParser(
		description="Process images in ./icons directory to max 144x144 resolution."
	)
	parser.add_argument(
		"--force",
		action="store_true",
		help="Force reformatting of all images, even if they match the target format and size.",
	)

	# Quality settings
	parser.add_argument(
		"--quality",
		type=int,
		default=99,
		help="PNG quality (0-100, higher is better). Default: 99",
	)

	# Palette settings
	parser.add_argument(
		"--no-palette",
		action="store_false",
		dest="use_palette",
		help="Disable palette optimization",
	)
	parser.add_argument(
		"--palette-colors",
		type=int,
		default=256,
		help="Number of colors to use in palette (2-256). Default: 256",
	)

	args = parser.parse_args()

	input_dir = "./icons"
	if not os.path.exists(input_dir):
		print(f"Error: Directory '{input_dir}' does not exist.")
		return

	force_reformat = args.force

	total_files, modified_files, original_size, new_size = process_images(
		input_dir=input_dir,
		force_reformat=force_reformat,
		quality=args.quality,
		use_palette=args.use_palette,
		palette_colors=args.palette_colors,
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
