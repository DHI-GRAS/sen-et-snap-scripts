import click
import numpy as np

from pyTSEB import TSEB

import snappy_utils as su


@click.command()
@click.option('--sza_file', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--biophysical_file', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--min_frac_green', required=True, type=click.FloatRange(min=0.01, max=1))
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(sza_file, biophysical_file, min_frac_green, output_file):

    # Read the required data
    fapar, geo_coding = su.read_snappy_product(biophysical_file, 'fapar')
    lai = su.read_snappy_product(biophysical_file, 'lai')[0]
    sza = su.read_snappy_product(sza_file, 'sun_zenith')[0]

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

    su.write_snappy_product(output_file, [{'band_name': 'frac_green', 'band_data': f_g}],
                            'fracGreen', geo_coding)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
