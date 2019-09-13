import click
import numpy as np

from pyTSEB import TSEB

import snappy_utils as su


@click.command()
@click.option('--lst', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--lst_vza', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--lai', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--csp', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--fgv', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--ar', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--mi', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--nsr', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--li', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--mask', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--soil_roughness', required=True, type=click.Float)
@click.option('--alpha_pt', required=True, type=click.Float)
@click.option('--atmospheric_measurement_height', required=True, type=click.Float)
@click.option('--green_vegetation_emissivity', required=True, type=click.Float)
@click.option('--soil_emissivity', required=True, type=click.FLOAT)
@click.option('--save_component_fluxes', required=True, type=click.BOOL)
@click.option('--save_component_temperature', required=True, type=click.BOOL)
@click.option('--save_aerodynamic_parameters', required=True, type=click.BOOL)
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(lst, lst_vza, lai, csp, fgv, ar, mi, nsr, li, mask, soil_roughness,alpha_pt,
        atmospheric_measurement_height, green_vegetation_emissivity, soil_emissivity,
        save_component_fluxes, save_component_temperature, save_aerodynamic_parameters, 
        output_file):

    # Read the required data
    lst = su.read_snappy_product(lst, 'LST')[0]
    vza = su.read_snappy_product(lst_vza, 'vza')[0]
    lai, geo_coding = su.read_snappy_product(lai, 'lai')
    lad = su.read_snappy_product(csp, 'veg_inclination_distribution')[0]
    frac_cover = su.read_snappy_product(csp, 'veg_fractional_cover')[0]
    h_w_ratio = su.read_snappy_product(csp, 'veg_height_width_ratio')[0]
    leaf_width = su.read_snappy_product(csp, 'veg_leaf_width')[0]
    veg_height = su.read_snappy_product(csp, 'veg_height')[0]
    landcover_band = su.read_snappy_product(csp, 'igbp_classification')[0]
    frac_green = su.read_snappy_product(fgv, 'frac_green')[0]
    z_0M = su.read_snappy_product(ar, 'roughness_length')[0]
    d_0 = su.read_snappy_product(ar, 'zero-plane_displacement')[0]
    ta = su.read_snappy_product(mi, 'air_temperature')[0]
    u = su.read_snappy_product(mi, 'wind_speed')[0]
    ea = su.read_snappy_product(mi, 'vapour_pressure')[0]
    p = su.read_snappy_product(mi, 'air_pressure')[0]
    shortwave_rad_c = su.read_snappy_product(nsr, 'canopy_net_shortwave_radiation')[0]
    shortwave_rad_s = su.read_snappy_product(nsr, 'soil_net_shortwave_radiation')[0]
    longwave_irrad = su.read_snappy_product(li, 'longwave_irradiance')[0]
    mask = su.read_snappy_product(mask, 'mask')[0]

    # Model outputs
    t_s = np.full(lai.shape, np.nan)
    t_c = np.full(lai.shape, np.nan)
    t_ac = np.full(lai.shape, np.nan)
    h_s = np.full(lai.shape, np.nan)
    h_c = np.full(lai.shape, np.nan)
    le_s = np.full(lai.shape, np.nan)
    le_c = np.full(lai.shape, np.nan)
    g = np.full(lai.shape, np.nan)
    ln_s = np.full(lai.shape, np.nan)
    ln_c = np.full(lai.shape, np.nan)
    r_s = np.full(lai.shape, np.nan)
    r_x = np.full(lai.shape, np.nan)
    r_a = np.full(lai.shape, np.nan)
    u_friction = np.full(lai.shape, np.nan)
    mol = np.full(lai.shape, np.nan)
    n_iterations = np.full(lai.shape, np.nan)
    flag = np.full(lai.shape, 255)

    # ======================================
    # First process bare soil cases
    i = np.logical_and(lai <= 0, mask == 1)
    t_s[i] = lst[i]

    # Calculate soil fluxes
    [flag[i], ln_s[i], le_s[i], h_s[i], g[i], r_a[i], u_friction[i], mol[i],
    n_iterations[i]] = TSEB.OSEB(lst[i],
                                 ta[i],
                                 u[i],
                                 ea[i],
                                 p[i],
                                 shortwave_rad_s[i],
                                 longwave_irrad[i],
                                 soil_emissivity,
                                 z_0M[i],
                                 d_0[i],
                                 atmospheric_measurement_height,
                                 atmospheric_measurement_height,
                                 calcG_params=[[1], 0.35])

    # Set canopy fluxes to 0
    ln_c[i] = 0.0
    le_c[i] = 0.0
    h_c[i] = 0.0

    # ======================================
    # Then process vegetated cases
    i = np.logical_and(lai > 0, mask == 1)
    # Emissivity of canopy containing green and non-green elements.
    emissivity_veg = green_vegetation_emissivity * frac_green[i] + 0.91 * (1 - frac_green[i])

    # Caculate component fluxes
    [flag[i], t_s[i], t_c[i], t_ac[i], ln_s[i], ln_c[i], le_c[i], h_c[i], le_s[i], h_s[i],
    g[i], r_s[i], r_x[i], r_a[i], u_friction[i], mol[i],
    n_iterations[i]] = TSEB.TSEB_PT(lst[i],
                                    vza[i],
                                    ta[i],
                                    u[i],
                                    ea[i],
                                    p[i],
                                    shortwave_rad_c[i],
                                    shortwave_rad_s[i],
                                    longwave_irrad[i],
                                    lai[i],
                                    veg_height[i],
                                    emissivity_veg,
                                    soil_emissivity,
                                    z_0M[i],
                                    d_0[i],
                                    atmospheric_measurement_height,
                                    atmospheric_measurement_height,
                                    f_c=f_cover[i],
                                    f_g=frac_green[i],
                                    w_C=h_w_ratio[i],
                                    leaf_width=leaf_width[i],
                                    z0_soil=soil_roughness,
                                    alpha_PT=alpha_pt,
                                    x_LAD=lad[i],
                                    calcG_params=[[1], 0.35],
                                    resistance_form=[0, {}])

    # Calculate the bulk fluxes
    le = le_c + le_s
    h = h_c + h_s
    r_ns = shortwave_rad_c + shortwave_rad_s
    r_nl = ln_c + ln_s
    r_n = r_ns + r_nl

    band_data = [
            {'band_name': 'sensible_heat_flux', 'band_data': h},
            {'band_name': 'latent_heat_flux', 'band_data': le},
            {'band_name': 'ground_heat_flux', 'band_data': g},
            {'band_name': 'net_radiation', 'band_data': r_n},
            {'band_name': 'quality_flag', 'band_data': flag}
            ]

    if save_component_fluxes:
        band_data.extend(
                [
                    {'band_name': 'sensible_heat_flux_canopy', 'band_data': h_c},
                    {'band_name': 'sensible_heat_flux_soil', 'band_data': h_s},
                    {'band_name': 'latent_heat_flux_canopy', 'band_data': le_c},
                    {'band_name': 'latent_heat_flux_soil', 'band_data': le_s},
                    {'band_name': 'net_longwave_radiation_canopy', 'band_data': ln_c},
                    {'band_name': 'net_longwave_radiation_soil', 'band_data': ln_s}
                ]
        )
    if save_component_temperature:
        band_data.extend(
                [
                    {'band_name': 'temperature_canopy', 'band_data': t_c}, 
                    {'band_name': 'temperature_soil', 'band_data': t_s},
                    {'band_name': 'temperature_canopy_air', 'band_data': t_ac}
                ]
        )
    if save_aerodynamic_parameters:
        band_data.extend(
                [ 
                    {'band_name': 'resistance_surface', 'band_data': r_a}, 
                    {'band_name': 'resistance_canopy', 'band_data': r_x},
                    {'band_name': 'resistance_soil', 'band_data': r_s},
                    {'band_name': 'friction_velocity', 'band_data': u_friction},
                    {'band_name': 'monin_obukhov_length', 'band_data': mol}
                ]
        )
    
    su.write_snappy_product(output_file,band_data, turbulentFluxes, geo_coding)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
