import click
import numpy as np

from pyTSEB import TSEB

import snappy_utils as su
import snappy


def _estimate_param_value(landcover, lut, band): 
    param_value = np.ones(landcover.shape) + np.nan

    for lc_class in np.unique(landcover[~np.isnan(landcover)]):
        lc_pixels = np.where(landcover == lc_class)
        lc_index = lut['landcover_class'].index(lc_class)
        param_value[lc_pixels] = lut[band][lc_index]
    return param_value


@click.command()
@click.option('--landcover_map', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--lai_map', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--fgv_map', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--landcover_band', required=True)
@click.option('--lookup_table', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--produce_vh',required=True, type=click.BOOL)
@click.option('--produce_fc',required=True, type=click.BOOL)
@click.option('--produce_chwr',required=True, type=click.BOOL)
@click.option('--produce_lw',required=True, type=click.BOOL)
@click.option('--produce_lid',required=True, type=click.BOOL)
@click.option('--produce_igbp',required=True, type=click.BOOL)
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(landcover_map, lai_map, fgv_map, landcover_band, lookup_table, produce_vh, produce_fc,
        produce_chwr, produce_lw, produce_lid, produce_igbp, output_file):

    # Read the required data

    PARAMS = ['veg_height', 'lai_max', 'is_herbaceous', 'veg_fractional_cover',
              'veg_height_width_ratio', 'veg_leaf_width', 'veg_inclination_distribution',
              'igbp_classification'
              ]
    
    landcover, geo_coding = su.read_snappy_product(landcover_map, landcover_band)
    lai = su.read_snappy_product(lai_map, 'lai')[0]
    fg = su.read_snappy_product(fgv_map, 'frac_green')[0]
    with open(lookup_table, 'r') as fp:
        lines = fp.readlines()
    headers = lines[0].rstrip().split(';')
    values = [x.rstrip().split(';') for x in lines[1:]]
    lut = {key: [float(x[idx]) for x in values if len(x) == len(headers)]
            for idx, key in enumerate(headers)}

    for param in PARAMS:
        if param not in lut.keys():
            print(f'Error: Missing {param} in the look-up table')
            return

    band_data = []

    if produce_vh:
        param_value = np.ones(landcover.shape) + np.nan

        for lc_class in np.unique(landcover[~np.isnan(landcover)]):
            lc_pixels = np.where(landcover == lc_class)
            lc_index = lut["landcover_class"].index(lc_class)
            param_value[lc_pixels] = lut['veg_height'][lc_index]

            # Vegetation height in herbaceous vegetation depends on plant area index
            if lut["is_herbaceous"][lc_index] == 1:
                pai = lai / fg
                pai = pai[lc_pixels]
                param_value[lc_pixels] = \
                    0.1 * param_value[lc_pixels] + 0.9 * param_value[lc_pixels] *\
                    np.minimum((pai / lut['veg_height'][lc_index])**3.0, 1.0)
        band_data.append({'band_name': 'veg_height', 'band_data': param_value})
    
    if produce_fc:
        band_name = 'veg_fractional_cover'
        param_value = _estimate_param_value(landcover, lut, band_name)
        band_data.append({'band_name': band_name, 'band_data': param_value})
    
    if produce_chwr:
        band_name = 'veg_height_width_ratio'
        param_value = _estimate_param_value(landcover, lut, band_name)
        band_data.append({'band_name': band_name, 'band_data': param_value})

    if produce_lw:
        band_name = 'veg_leaf_width'
        param_value = _estimate_param_value(landcover, lut, band_name)
        band_data.append({'band_name': band_name, 'band_data': param_value})

    if produce_lid:
        band_name = 'veg_inclination_distribution'
        param_value = _estimate_param_value(landcover, lut, band_name)
        band_data.append({'band_name': band_name, 'band_data': param_value})

    if produce_igbp:
        band_name = 'igbp_classification'
        param_value = _estimate_param_value(landcover, lut, band_name)
        band_data.append({'band_name': band_name, 'band_data': param_value})

    su.write_snappy_product(output_file, band_data, 'landcoverParams', geo_coding)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
