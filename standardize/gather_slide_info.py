# Authors: Caleb Grenko and Siddhesh Thakur
# Caleb.Grenko@pennmedicine.upenn.edu, SiddheshPravin.Thakur@pennmedicine.upenn.edu
# Disclaimer: This is experimental code and has not been validated. Treat it as such.
#
import os
import argparse
from openslide import OpenSlide, OpenSlideUnsupportedFormatError


def get_level_for_downsample(image, downsample):
    for level in range(image.level_count):
        if image.level_downsamples[level] >= (downsample - 0.1) and \
                image.level_downsamples[level] <= (downsample + 0.1):
            return level
    else:
        return -1


def main(input_path, output_tsv, patients):
    tsv_file = open(output_tsv, 'w+')
    tsv_file.write(
        'PID\twsi_path\tobjective-power\tmpp-x\tmpp-y\tcorrect-power-dims\theight\twidth\tlevel_count\tselected_level\tselected_level_height\tselected_level_width\test_magnifications\n')
    for patient in patients:
        print(os.path.basename(patient.strip('.svs')))
        wsi_path = os.path.join(input_path, patient)
        os_image = OpenSlide(wsi_path)
        level_count = os_image.level_count
        properties = os_image.properties
        items = dict(properties.items())
        try:
            obj_pow = items['openslide.objective-power']
            mpp_x = round(float(items['openslide.mpp-x']), 2)
            mpp_y = round(float(items['openslide.mpp-y']), 2)
            correct_power_dims = False
            if obj_pow == '40' and mpp_x == 0.25 and mpp_y == 0.25:
                correct_power_dims = True
            elif obj_pow == '20' and mpp_x == 0.5 and mpp_y == 0.5:
                correct_power_dims = True
            elif obj_pow == '10' and mpp_x == 1 and mpp_y == 1:
                correct_power_dims = True
            elif obj_pow == '5' and mpp_x == 2 and mpp_y == 2:
                correct_power_dims = True

            level_dim_factors = []
            estimated_magnifications = []
            current_level_dims = (0, 0)
            estimated_magnification = float(obj_pow)
            estimated_mpp = mpp_x
            print("\tLevel Downsamples:", os_image.level_downsamples)
            print("\tLevel:    ", end="")
            print("\tLvl. Dims:", end="\t")
            print("\tEst. Mag: ", end="\n")
            for level in range(os_image.level_count):
                if len(level_dim_factors) == 0:
                    level_dim_factors.append(1)
                    base_level_dim_proportion = os_image.level_dimensions[0][0] / os_image.level_dimensions[0][1]
                    estimated_magnification = float(obj_pow)
                    estimated_magnifications.append(estimated_magnification)
                else:
                    inverse_downsample_factor = os_image.level_dimensions[level][0] / os_image.level_dimensions[0][0]
                    level_dim_proportion = os_image.level_dimensions[level][0] / os_image.level_dimensions[level][1]
                    assert round(base_level_dim_proportion) == round(
                        level_dim_proportion), "Dimensions at level %i mismatched from base" % level
                    level_dim_factors.append(inverse_downsample_factor)
                    assert round(os_image.level_downsamples[level]) == round(
                        1 / inverse_downsample_factor), "Mismatched downsample factor calculated (%f) vs. metadata (%f)" % (
                    round(1 / inverse_downsample_factor), round(os_image.level_downsamples[level]))
                    estimated_magnification = float(obj_pow) * inverse_downsample_factor
                    estimated_magnifications.append(round(estimated_magnification, 2))
                print("\t", end="")
                print(str(level), end="\t\t")
                print(str(os_image.level_dimensions[level]), end="\t\t")
                print(str(round(estimated_magnification, 2)), end="\n")

            height, width = os_image.dimensions
            # These numbers can be updated but using from experience
            selected_level = get_level_for_downsample(os_image, 4)
            selected_level_height, selected_level_width = os_image.level_dimensions[selected_level]
            tsv_file.write(patient + '\t' + wsi_path + '\t' + \
                           str(obj_pow) + '\t' + \
                           str(mpp_x) + '\t' + str(mpp_y) + \
                           '\t' + str(correct_power_dims) + \
                           '\t' + str(height) + '\t' + str(width) + \
                           '\t' + str(level_count) + \
                           '\t' + str(selected_level) + \
                           '\t' + str(selected_level_height) + \
                           '\t' + str(selected_level_width) + \
                           '\t' + str(estimated_magnifications) + \
                           '\t' + str(os_image.level_dimensions) + '\n')
        except KeyError as k:
            print(patient + ',Error in one of the keys: %s\n' % k)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input_path', dest='input_path',
                        help="input path for the tissues", required=True)
    parser.add_argument('-o', '--output_tsv', dest='output_tsv',
                        help="output tsv file to be created", required=True)
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_path)
    output_tsv = os.path.abspath(args.output_tsv)
    patients = os.listdir(input_path)

    main(input_path, output_tsv, patients)