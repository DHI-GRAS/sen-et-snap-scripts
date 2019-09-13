import click
import numpy as np

import snappy_utils as su
from pyTSEB import meteo_utils as met


@click.command()
@click.option('--ief_file', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--mi_file', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(ief_file, mi_file, output_file):

    # Read the required data
    le_band, geo_coding = su.read_snappy_product(ief_file, 'latent_heat_flux')
    sdn_band = su.read_snappy_product(mi_file, 'clear_sky_solar_radiation')[0]
    sdn_24_band = su.read_snappy_product(mi_file, 'average_daily_solar_irradiance')[0]

    le = np.array(le_band)
    sdn = np.array(sdn_band)
    sdn_24 = np.array(sdn_24_band)

    et_daily = met.flux_2_evaporation(sdn_24 * le / sdn, T_K=20+273.15, time_domain=24)
    
    su.write_snappy_product(output_file, [{'band_name': 'daily_evapotranspiration', 'band_data': et_daily}],
                            'dailySpectra', geo_coding)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
