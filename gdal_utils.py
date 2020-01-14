import tempfile
import os.path as pth
import numpy as np

from pyDMS.pyDMSUtils import saveImg, openRaster, getRasterInfo

#Since the conda environment is not active
#make sure to set the env_variables needed for gdal
import os
cur_path =  os.path.dirname(os.path.abspath(__file__))
if os.name == 'nt':
    os.environ["PROJ_LIB"] = os.path.join(cur_path, "../Library/share/proj")
    os.environ["GDAL_DATA"] = os.path.join(cur_path, "../Library/share/gdal")
else:
    os.environ["PROJ_LIB"] = os.path.join(cur_path, "../share/proj")
    os.environ["GDAL_DATA"] = os.path.join(cur_path, "../share/gdal")
from osgeo import gdal


def slope_from_dem(dem_file_path, output=None):

    if not output:
        output = dem_file_path.replace('.tif', '_slope.tif')

    gdal.DEMProcessing(output, dem_file_path, "slope", computeEdges=True)
    return output


def aspect_from_dem(dem_file_path, output=None):

    if not output:
        output = pth.splitext(dem_file_path)[0]+'_aspect.tif'

    gdal.DEMProcessing(output, dem_file_path, "aspect", computeEdges=True)
    return output


def save_image(data, geotransform, projection, filename):
    return saveImg(data, geotransform, projection, filename)


def resample_with_gdalwarp(src, template, resample_alg="cubicspline"):
    # Get template projection, extent and resolution
    proj, gt, sizeX, sizeY, extent, _ = raster_info(template)

    # Resample with GDAL warp
    out_ds = gdal.Warp("",
                       src,
                       format="MEM",
                       dstSRS=proj,
                       xRes=gt[1],
                       yRes=gt[5],
                       outputBounds=extent,
                       resampleAlg=resample_alg)
    return out_ds


def raster_info(raster):
    return getRasterInfo(raster)


def raster_data(raster, bands=1, rect=None):

    def _read_band(fid, band, rect):
        if rect:
            return fid.GetRasterBand(band).ReadAsArray(rect.x, rect.y, rect.width, rect.height)
        else:
            return fid.GetRasterBand(band).ReadAsArray()

    fid, closeOnExit = openRaster(raster)
    if type(bands) == int:
        bands = [bands]

    data = None
    for band in bands:
        if data is None:
            data = _read_band(fid, band, rect)
        else:
            data = np.dstack((data, _read_band(fid, band, rect)))

    if closeOnExit:
        fid = None

    return data


def merge_raster_layers(input_list, output_filename, separate=False):
    merge_list = []
    for input_file in input_list:
        bands = raster_info(input_file)[5]
        # GDAL Build VRT cannot stack multiple multi-band images, so they have to be split into
        # multiple singe-band images first.
        if bands > 1:
            for band in range(1, bands+1):
                temp_filename = tempfile.mkstemp(suffix="_"+str(band)+".vrt")[1]
                gdal.BuildVRT(temp_filename, [input_file], bandList=[band])
                merge_list.append(temp_filename)
        else:
            merge_list.append(input_file)
    fp = gdal.BuildVRT(output_filename, merge_list, separate=separate)
    return fp
