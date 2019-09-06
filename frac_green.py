import numpy as np

from pyTSEB import TSEB

import snappy
from snappy import jpy, ProductIO, Product
Float = jpy.get_type('java.lang.Float')


def main(l2a_file, biophysical_file, min_frac_green, output_file):
    
    # Read the required data
    fapar, geo_coding = read_snappy_product(biophysical_file, 'fapar')
    lai = read_snappy_product(biophysical_file, 'lai')[0]
    sza = read_snappy_product(l2a_file, 'sun_zenith')[0]
    
    # Calculate fraction of vegetation which is green
    f_g = np.ones(lai.shape)
    # Iterate until f_g converges
    converged = np.zeros(lai.shape, dtype=bool)
    # For pixels where LAI or FAPAR are below tolerance threshold of the S2 biophysical
    # processor, assume that the soil is bare and f_g = 1
    converged[np.logical_or(lai <= 0.2, fapar <= 0.1)] = True
    for c in range(50):
        f_g_old = f_g.copy()
        fipar = TSEB.calc_F_theta_campbell(sza[~converged],
                                           lai[~converged]/f_g[~converged],
                                           w_C=1, Omega0=1, x_LAD=1)
        f_g[~converged] = fapar[~converged] / fipar
        f_g = np.clip(f_g, min_frac_green, 1.)
        converged = np.logical_or(np.isnan(f_g), np.abs(f_g - f_g_old) < 0.02)
        if np.all(converged):
            break
        
    write_snappy_product(output_file, [{'band_name': 'frac_green', 'band_data': f_g}], 'fracGreen',
                         geo_coding)

    
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
    product.setGeoCoding(geo_coding)
    for b in bands:
        band = product.addBand(b['band_name'], Float)
        band.setPixels(0, 0, width, height, b['band_data'])
    ProductIO.writeProduct(product, file_path, 'GeoTIFF')

class FracGreenOp:
    def __init__(self):
        pass

    def initialize(self, context):
        # Read source products
        biophys_prod = context.getSourceProduct("plant_biophysical_properties")
        self.fapar_band = biophys_prod.getBand("fapar")
        self.lai_band = biophys_prod.getBand("lai")
        l2a_prod = context.getSourceProduct("sun_zenith_angle_product")
        self.sza_band = l2a_prod.getBand("sun_zenith")

        # Get parameters
        self.min_f_g = context.getParameter("minimum_frac_green")

        # Setup target product
        width = self.lai_band.getRasterWidth()
        height = self.lai_band.getRasterHeight()
        fg_prod = snappy.Product("fracGreen", "fracGreen", width, height)
        snappy.ProductUtils.copyGeoCoding(self.lai_band, fg_prod)
        fg_band = fg_prod.addBand("frac_green", snappy.ProductData.TYPE_FLOAT32)
        fg_band.setDescription("Fraction of vegetation which is green")
        fg_band.setNoDataValue(Float.NaN)
        fg_band.setNoDataValueUsed(True)
        context.setTargetProduct(fg_prod)

    def dispose(self, context):
        pass

    def computeTile(self, context, band, tile):
        rect = tile.getRectangle()
        fapar_tile = context.getSourceTile(self.fapar_band, rect)
        fapar = np.array(fapar_tile.getSamplesFloat())
        lai_tile = context.getSourceTile(self.lai_band, rect)
        lai = np.array(lai_tile.getSamplesFloat())
        sza_tile = context.getSourceTile(self.sza_band, rect)
        sza = np.array(sza_tile.getSamplesFloat())
        f_g = np.ones(lai.shape)

        # Iterate until f_g converges
        converged = np.zeros(lai.shape, dtype=bool)
        # For pixels where LAI or FAPAR are below tolerance threshold of the S2 biophysical
        # processor, assume that the soil is bare and f_g = 1
        converged[np.logical_or(lai <= 0.2, fapar <= 0.1)] = True
        for c in range(50):
            f_g_old = f_g.copy()
            fipar = TSEB.calc_F_theta_campbell(sza[~converged],
                                               lai[~converged]/f_g[~converged],
                                               w_C=1, Omega0=1, x_LAD=1)
            f_g[~converged] = fapar[~converged] / fipar
            f_g = np.clip(f_g, self.min_f_g, 1.)
            converged = np.logical_or(np.isnan(f_g), np.abs(f_g - f_g_old) < 0.02)
            if np.all(converged):
                break

        tile.setSamples(f_g)
