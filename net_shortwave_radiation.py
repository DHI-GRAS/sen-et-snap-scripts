import click
import numpy as np

import pyTSEB.net_radiation as rad
import pyTSEB.clumping_index as ci

import snappy_utils as su


@click.command()
@click.option('--lsp_product', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--lai_product', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--csp_product', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--mi_product', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--sza_product', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--soil_ref_vis', required=True, type=click.FLOAT)
@click.option('--soil_ref_nir', required=True, type=click.FLOAT)
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(lsp_product, lai_product, csp_product, mi_product, sza_product, soil_ref_vis,
        soil_ref_nir ,output_file):
    

    
    refl_vis_c, geo_coding = su.read_snappy_product(lsp_product, 'refl_vis_c')
    refl_nir_c = su.read_snappy_product(lsp_product, 'refl_nir_c')[0]
    trans_vis_c = su.read_snappy_product(lsp_product, 'trans_vis_c')[0] 
    trans_nir_c = su.read_snappy_product(lsp_product, 'trans_nir_c')[0]

    lai = su.read_snappy_product(lai_product, 'lai')[0]


    lad = su.read_snappy_product(csp_product, 'veg_inclination_distribution')[0]
    frac_cover = su.read_snappy_product(csp_product, 'veg_fractional_cover')[0]
    hw_ratio = su.read_snappy_product(csp_product, 'veg_height_width_ratio')[0]
    
    
    p = su.read_snappy_product(mi_product, 'air_pressure')[0]
    irradiance = su.read_snappy_product(mi_product, 'clear_sky_solar_irradiance')[0]
    
    sza = su.read_snappy_product(sza_product, 'sza')[0]
   
    net_rad_c = np.zeros(lai.shape)
    net_rad_s = np.zeros(lai.shape)

    #Estimate diffuse and direct irradiance
    difvis, difnir, fvis, fnir = rad.calc_difuse_ratio(irradiance, sza, p)
    skyl = difvis * fvis + difnir * fnir
    irradiance_dir = irradiance * (1.0 - skyl)
    irradiance_dif = irradiance * skyl

    # Net shortwave radition for bare soil
    i = lai <= 0
    spectra_soil = fvis[i] * soil_ref_vis + fnir[i] * soil_ref_nir
    net_rad_s[i] = (1. - spectra_soil) * (irradiance_dir[i] + irradiance_dif[i])
    
    # Net shortwave radiation for vegetated areas
    i = lai > 0
    F = lai[i] / frac_cover[i] 
    # Clumping index
    omega0 = ci.calc_omega0_Kustas(lai[i], frac_cover[i], lad[i], isLAIeff=True)
    omega = ci.calc_omega_Kustas(omega0, sza[i], hw_ratio[i])
    lai_eff = F * omega
    [net_rad_c[i], net_rad_s[i]] = rad.calc_Sn_Campbell(lai[i],
                                                        sza[i],
                                                        irradiance_dir[i],
                                                        irradiance_dif[i],
                                                        fvis[i],
                                                        fnir[i],
                                                        refl_vis_c[i],
                                                        trans_vis_c[i],
                                                        refl_nir_c[i],
                                                        trans_nir_c[i],
                                                        soil_ref_vis,
                                                        soil_ref_nir,
                                                        lad[i],
                                                        lai_eff
                                                        )
    

    band_data = [

            {'band_name': 'net_shortwave_radiation_canopy', 'band_data': net_rad_c}
            {'band_name': 'net_shortwave_radiation_soil', 'band_data': net_rad_s}
    ]

    su.write_snappy_product(output_file, band_data, 'netShortwaveRadiation', geo_coding)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
