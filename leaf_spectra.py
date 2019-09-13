import click
import numpy as np

import snappy_utils as su


def cab_to_vis_spectrum(cab,
                            coeffs_wc_rho_vis=[0.14096573, -0.09648072, -0.06328343],
                            coeffs_wc_tau_vis=[0.08543707, -0.08072709, -0.06562554]):

    rho_leaf_vis = watercloud_model(cab, *coeffs_wc_rho_vis)
    tau_leaf_vis = watercloud_model(cab, *coeffs_wc_tau_vis)

    rho_leaf_vis = np.clip(rho_leaf_vis, 0, 1)
    tau_leaf_vis = np.clip(tau_leaf_vis, 0, 1)

    return rho_leaf_vis, tau_leaf_vis


def cw_to_nir_spectrum(cw,
                           coeffs_wc_rho_nir=[0.38976106, -0.17260689, -65.7445699],
                           coeffs_wc_tau_nir=[0.36187620, -0.18374560, -65.3125878]):

    rho_leaf_nir = watercloud_model(cw, *coeffs_wc_rho_nir)
    tau_leaf_nir = watercloud_model(cw, *coeffs_wc_tau_nir)

    rho_leaf_nir = np.clip(rho_leaf_nir, 0, 1)
    tau_leaf_nir = np.clip(rho_leaf_nir, 0, 1)

    return rho_leaf_nir, tau_leaf_nir



def watercloud_model(param, a, b, c):

    result = a + b * (1.0 - np.exp(c * param))

    return result

@click.command()
@click.option('--biophysical_file', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(biophysical_file, output_file):

    # Read the required data
    lai_cab, geo_coding = su.read_snappy_product(biophysical_file, 'lai_cab')
    lai_cw = su.read_snappy_product(biophysical_file, 'lai_cw')[0]
    
    cab = np.clip(np.array(lai_cab), 0.0, 140.0)
    refl_vis, trans_vis = cab_to_vis_spectrum(cab)

    cw = np.clip(np.array(lai_cw), 0.0, 0.1)
    refl_nir, trans_nir = cw_to_nir_spectrum(cw)

    su.write_snappy_product(output_file, [
        {'band_name': 'refl_vis_c', 'band_data': refl_vis},
        {'band_name': 'refl_nir_c', 'band_data': refl_nir},
        {'band_name': 'trans_vis_c', 'band_data': trans_vis},
        {'band_name': 'trans_nir_c', 'band_data': trans_nir}
        ],
        'leafSpectra', geo_coding)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
