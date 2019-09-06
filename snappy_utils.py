import numpy as np

import os
import sys
sys.path.append(os.path.join(os.path.expanduser("~"), ".snap", "snap-python"))
from snappy import ProductIO, Product, ProductData #, jpy
#Float = jpy.get_type('java.lang.Float')


def read_snappy_product(file_path, band_name):
    prod = ProductIO.readProduct(file_path)
    width = prod.getSceneRasterWidth()
    height = prod.getSceneRasterHeight()
    geo_coding = prod.getSceneGeoCoding()
    data = np.empty((width, height))
    band = prod.getBand(band_name)
    band.readPixels(0, 0, width, height, data)
    prod.closeIO()
    return data, geo_coding


def write_snappy_product(file_path, bands, product_name, geo_coding):
    (width, height) = bands[0]['band_data'].shape
    product = Product(product_name, product_name, width, height)
    product.setSceneGeoCoding(geo_coding)
    for b in bands:
        band = product.addBand(b['band_name'], ProductData.TYPE_FLOAT32)
        band.setPixels(0, 0, width, height, b['band_data'].astype(np.float32).tolist())
    ProductIO.writeProduct(product, file_path, 'GeoTIFF')
