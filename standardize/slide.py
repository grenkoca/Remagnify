import os
from openslide import OpenSlide
from skimage.filters import gaussian
from skimage.io import imread, imsave
import numpy as np
import os.path as path
from tempfile import mkdtemp
from PIL import Image

GAUSSIAN_SIGMA = 1.5
Image.MAX_IMAGE_PIXELS = None


class Slide(OpenSlide):
    def __init__(self, fname, *args, **kwargs):
        super().__init__(filename=fname)
        self.estimated_magnifications = []
        self.proxy_path = None

        self.gather_image_magnifications()

    def add_proxy(self, fpath):
        assert os.path.isfile(
            fpath), "File not found (or is directory): %s" % fpath
        self.proxy_path = fpath

    def gather_image_magnifications(self):
        print("Level Downsamples:", self.level_downsamples)
        print("Level:    ", end="")
        print("Lvl. Dims:", end="\t")
        print("Est. Mag: ", end="\n")
        base_level_dim_proportion = 1
        level_dim_factors = []
        obj_pow = self.properties['openslide.objective-power']
        for level in range(self.level_count):
            if len(level_dim_factors) == 0:
                level_dim_factors.append(1)
                base_level_dim_proportion = self.level_dimensions[0][0] / \
                    self.level_dimensions[0][1]
                estimated_magnification = float(obj_pow)
                self.estimated_magnifications.append(estimated_magnification)
            else:
                inverse_downsample_factor = self.level_dimensions[level][0] / \
                    self.level_dimensions[0][0]
                level_dim_proportion = self.level_dimensions[level][0] / \
                    self.level_dimensions[level][1]
                assert round(base_level_dim_proportion) == round(
                    level_dim_proportion), "Dimensions at level %i mismatched from base" % level
                level_dim_factors.append(inverse_downsample_factor)
                assert round(self.level_downsamples[level]) == round(
                    1 / inverse_downsample_factor), "Mismatched downsample factor calculated (%f) vs. metadata (%f)" % (
                    round(1 / inverse_downsample_factor), round(self.level_downsamples[level]))
                estimated_magnification = float(
                    obj_pow) * inverse_downsample_factor
                self.estimated_magnifications.append(
                    round(estimated_magnification, 2))
            print("", end="")
            print(str(level), end="\t\t")
            print(str(self.level_dimensions[level]), end="\t\t")
            print(str(round(estimated_magnification, 2)), end="\n")

    def save_downsampled(
            self,
            fpath,
            new_obj_power,
            blur_image=False,
            use_proxy=False):
        # TODO: Use memmap?
        if use_proxy:
            assert self.proxy_path is not None, "No proxy set but `use_proxy` set to True in save_downsampled."
            slide_image = imread(self.proxy_path)
            # assume base image is highest resolution
            original_obj_power = self.estimated_magnifications[0]
        else:
            if float(new_obj_power) in self.estimated_magnifications:
                print("\tUsing magnification found in slide object")
                obj_power_index = self.estimated_magnifications.index(
                    new_obj_power)
                slide_image = self.read_region(
                    (0, 0), obj_power_index, self.level_dimensions[obj_power_index])
                original_obj_power = self.estimated_magnifications[obj_power_index]
            else:
                slide_image = self.read_region((0, 0), 0, self.dimensions)
                original_obj_power = self.estimated_magnifications[0]
            slide_image = np.array(slide_image)[:, :, :3]

        if blur_image:
            filename = path.join(mkdtemp(), 'newfile.dat')
            fp = np.memmap(
                filename,
                dtype=np.uint8,
                mode="w+",
                shape=slide_image.shape)
            fp[:] = slide_image[:]
            slide_image = gaussian(
                fp,
                sigma=GAUSSIAN_SIGMA,
                preserve_range=True,
                multichannel=True)

        fold_change = new_obj_power / original_obj_power
        new_dimensions = int(
            slide_image.shape[0] * fold_change), int(slide_image.shape[1] * fold_change)
        step = round(1 / fold_change)
        downsampled_image = slide_image[::step, ::step, :]

        print(
            "\tNew dimensions for %sx -> %sx: %s (actual: %s)" %
            (original_obj_power,
             new_obj_power,
             new_dimensions,
             downsampled_image.shape))
        try:
            imsave(fpath, downsampled_image)
        except Exception as e:
            raise IOError("Could not save image: %s" % e)
