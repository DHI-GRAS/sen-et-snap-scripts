import click
import numpy as np

import pyTSEB.net_radiation as rad
import snappy_utils as su


@click.command()
@click.option('--meteo_product', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--at_band', required=True)
@click.option('--vp_band', required=True)
@click.option('--ap_band', required=True)
@click.option('--at_height', required=True, type=click.FLOAT)
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(meteo_product, at_band, vp_band, ap_band, at_height, output_file):
    

    at, geo_coding = su.read_snappy_product(meteo_product, at_band)
    at = at.astype(np.float32)
    vp = su.read_snappy_product(meteo_product, vp_band)[0].astype(np.float32)
    ap = su.read_snappy_product(meteo_product, ap_band)[0].astype(np.float32)

    irrad = rad.calc_longwave_irradiance(vp, at, ap, at_height)
    
    band_data = [
            {'band_name': 'longwave_irradiance', 'band_data': irrad}
    ]

    su.write_snappy_product(output_file, band_data, 'longwaveIrradiance', geo_coding)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
