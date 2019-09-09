import numpy as np

import os
import sys
sys.path.append(os.path.join(os.path.expanduser("~"), ".snap", "snap-python"))
from snappy import ProductIO, Product, ProductData, String


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
    (width, height) = bands[0]['band_data'].shape
    product = Product(product_name, product_name, width, height)
    product.setSceneGeoCoding(geo_coding)

    # Ensure that output is saved in BEAM-DIMAP format, otherwise writeHeader does not work.
    file_path = os.path.splitext(file_path)[0] + '.dim'

    # Bands have to be created before header is written but header has to be written before band
    # data is written.
    for b in bands:
        band = product.addBand(b['band_name'], ProductData.TYPE_FLOAT32)
    product.setProductWriter(ProductIO.getProductWriter('BEAM-DIMAP'))
    product.writeHeader(String(file_path))
    for b in bands:
        band = product.getBand(b['band_name'])
        band.writePixels(0, 0, width, height, b['band_data'])
    product.closeIO()
