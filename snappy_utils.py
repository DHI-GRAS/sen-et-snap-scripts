import numpy as np

import os
import sys
sys.path.append(os.path.join(os.path.expanduser("~"), ".snap", "snap-python"))
from snappy import ProductIO, Product, ProductData, ProductUtils, String


def read_snappy_product(file_path, band_name):
    prod = ProductIO.readProduct(file_path)
    width = prod.getSceneRasterWidth()
    height = prod.getSceneRasterHeight()
    geo_coding = prod.getSceneGeoCoding()
    data = np.empty((width, height))
    band = prod.getBand(band_name)
    try:
        band.readPixels(0, 0, width, height, data)
    except AttributeError:
        prod.closeIO()
        raise RuntimeError(file_path + " does not contain band " + band_name)
    prod.closeIO()
    return data, geo_coding


def write_snappy_product(file_path, bands, product_name, geo_coding):
    try:
        (width, height) = bands[0]['band_data'].shape
    except AttributeError:
        raise RuntimeError(bands[0]['band_name'] + "contains no data.")
    product = Product(product_name, product_name, width, height)
    product.setSceneGeoCoding(geo_coding)

    # Ensure that output is saved in BEAM-DIMAP format, otherwise writeHeader does not work.
    file_path = os.path.splitext(file_path)[0] + '.dim'

    # Bands have to be created before header is written but header has to be written before band
    # data is written.
    for b in bands:
        band = product.addBand(b['band_name'], ProductData.TYPE_FLOAT32)
        if 'description' in b.keys():
            band.setDescription(b['description'])
        if 'unit' in b.keys():
            band.setUnit(b['unit'])
    product.setProductWriter(ProductIO.getProductWriter('BEAM-DIMAP'))
    product.writeHeader(String(file_path))
    for b in bands:
        band = product.getBand(b['band_name'])
        band.writePixels(0, 0, width, height, b['band_data'])
    product.closeIO()


def copy_bands_to_file(src_file_path, dst_file_path, bands):
    # Get info from source produc
    src_prod = ProductIO.readProduct(src_file_path)
    prod_name = src_prod.getName()
    prod_type = src_prod.getProductType()
    width = src_prod.getSceneRasterWidth()
    height = src_prod.getSceneRasterHeight()

    # Copy geocoding and selected bands from source to destination product
    dst_prod = Product(prod_name, prod_type, width, height)
    ProductUtils.copyGeoCoding(src_prod.getBandAt(0), dst_prod)
    for band in bands:
        r = ProductUtils.copyBand(band, src_prod, dst_prod, True)
        if r is None:
            src_prod.closeIO()
            raise RuntimeError(src_file_path + " does not contain band " + band)

    # Write destination product to disk
    ext = os.path.splitext(dst_file_path)[1]
    if ext == '.dim':
        file_type = 'BEAM_DIMAP'
    elif ext == '.nc':
        file_type = 'NetCDF-CF'
    elif ext == '.tif':
        file_type = 'GeoTIFF'
    else:
        file_type = 'GeoTIFF'
    ProductIO.writeProduct(dst_prod, dst_file_path, file_type)
    src_prod.closeIO()
    dst_prod.closeIO()
