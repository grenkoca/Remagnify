import os

import argparse
from standardize import Slide, gather_info
from glob import glob
import warnings
from pathlib import Path
import signal
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch objective power standardization for WSIs.")

    parser.add_argument(
        "-s",
        "--slides",
        type=str,
        dest="original_folder",
        required=True,
        help="Folder where openslide supported files are stored. Images can be nested in subfolders.")
    parser.add_argument(
        "-i",
        "--save_info",
        type=bool,
        dest="save_info",
        required=False,
        default=True,
        help="Save original slide information to .tsv file. `True` or `False`. Output .tsv file will be saved to" +
        " {output_folder}/batch_info.tsv")
    parser.add_argument(
        "-op",
        "--objective_powers",
        nargs='+',
        type=int,
        dest="objective_powers",
        required=True,
        help="Objective powers to resample image to. Can be n integers seperated by spaces.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        dest="output",
        required=True,
        help="Proxy images. same as --slides, except they are assumed as flat images with the same" +
        " dimensions as the base image file of the slide. This is helpful if you have modified the" +
        " base images of WSIs (with annotations, etc.) and stored them as separate image files.")
    parser.add_argument(
        "-p",
        "--proxies",
        type=str,
        dest="proxy_folder",
        required=False,
        help="Output directory. This will have one subfolder per slide, and each slide folder will" +
        " have one folder per resolution input from --objective_powers.")

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    # Parse input arguments and sort by name.
    input_args = parse_args()
    original_slides = sorted(
        glob(
            input_args.original_folder +
            "*.svs",
            recursive=True))

    if input_args.save_info:
        print()
        print(('=' * 23), 'GENERATING SUMMARY', ('=' * 23), end='\n')

        os.makedirs(input_args.output, exist_ok=True)
        pre_tsv_path = os.path.join(input_args.output, "pre_standardization_batch_info.tsv")
        gather_info(input_args.original_folder, pre_tsv_path, original_slides)
        print()
        print(('=' * 25), 'SUMMARY WRITTEN', ('=' * 25))
        print(' Output Path: %s' % Path(pre_tsv_path).resolve(), end='\n\n')

        def signal_handler(signal, frame):
            print("\n", str(signal), "CAUGHT, TERMINATING...")
            print()
            print(('=' * 23), 'GENERATING SUMMARY', ('=' * 23), end='\n')
            post_tsv_path = os.path.join(input_args.output, "post_standardization_batch_info.tsv")
            new_slides = sorted(
                glob(
                    input_args.output +
                    "*.tiff",
                    recursive=True))
            gather_info(input_args.original_folder, post_tsv_path, new_slides)
            print()
            print(('=' * 25), 'SUMMARY WRITTEN', ('=' * 25))
            print(' Output Path: %s' % Path(post_tsv_path).resolve(), end='\n\n')
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

    # If a folder of proxy images is given, then pair up the original WSIs and
    # proxy images.
    if input_args.proxy_folder is not None:
        cleaned_slides = sorted(
            glob(
                input_args.proxy_folder +
                "*.tiff",
                recursive=True))
        # If there is a different number of proxies and cleaned slides, raise
        # an assertion.
        assert len(original_slides) == len(
            cleaned_slides), "%d original slide files found, but %d proxies found."

        # Pair proxies and slides up and make sure they have the same slide ID
        for slide_path, cleaned_path in list(
                zip(original_slides, cleaned_slides)):
            slide_id_original = slide_path.split(".svs")[0].split("/")[-1]
            slide_id_cleaned = cleaned_path.split(
                "_overlay.tiff")[0].split("/")[-1]
            if not slide_id_cleaned == slide_id_cleaned:
                warnings.warn(
                    "Slide IDs not maching for %s and %s" %
                    (slide_id_original, slide_id_cleaned))

            resolution_folder_dict = {
                res: os.path.join(
                    input_args.output,
                    slide_id_original,
                    str(res) +
                    "x") for res in input_args.objective_powers}

            slide_object = Slide(slide_path)
            slide_object.add_proxy(cleaned_path)
            for objective_power, folder in resolution_folder_dict.items():
                os.makedirs(folder, exist_ok=True)
                output_file = folder + slide_id_original + ".tiff"
                slide_object.save_downsampled(
                    output_file, objective_power, blur_image=False, use_proxy=True)
    else:
        for slide_path in original_slides:
            slide_id_original = slide_path.split(".svs")[0].split("/")[-1]

            resolution_folder_dict = {
                res: os.path.join(
                    input_args.output,
                    slide_id_original,
                    str(res) +
                    'x') for res in input_args.objective_powers}

            slide_object = Slide(slide_path)
            for objective_power, folder in resolution_folder_dict.items():
                os.makedirs(folder, exist_ok=True)
                output_file = folder + slide_id_original + ".tiff"
                slide_object.save_downsampled(
                    output_file, objective_power, blur_image=False, use_proxy=False)

    if input_args.save_info:
        print()
        print(('=' * 23), 'GENERATING SUMMARY', ('=' * 23), end='\n')
        post_tsv_path = os.path.join(input_args.output, "post_standardization_batch_info.tsv")
        new_slides = sorted(
            glob(
                input_args.output +
                "*.tiff",
                recursive=True))
        gather_info(input_args.original_folder, post_tsv_path, new_slides)
        print()
        print(('=' * 25), 'SUMMARY WRITTEN', ('=' * 25))
        print(' Output Path: %s' % Path(post_tsv_path).resolve(), end='\n\n')

