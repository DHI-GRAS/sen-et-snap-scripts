import click
import numpy as np

import pyTSEB.resistances as res
import snappy_utils as su


@click.command()
@click.option('--lai_map', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--landcover_params_map', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--soil_roughness', required=True, type=click.FLOAT)
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(lai_map, landcover_params_map, soil_roughness, output_file):
    
    lai, geo_coding = su.read_snappy_product(lai_map, 'lai')
    lai = lai.astype(np.float32)
    height = su.read_snappy_product(landcover_params_map, 'veg_height')[0].astype(np.float32)
    height_width_ratio = su.read_snappy_product(landcover_params_map, 'veg_height_width_ratio')[0].astype(np.float32)
    fractional_cover = su.read_snappy_product(landcover_params_map, 'veg_fractional_cover')[0].astype(np.float32)
    classification = su.read_snappy_product(landcover_params_map, 'igbp_classification')[0].astype(np.float32)
    
    z_OM = np.full(lai.shape, np.nan, np.float32)
    d_0 = np.full(lai.shape, np.nan, np.float32)

    i = lai <= 0
    z_OM[i] = soil_roughness
    d_0[i] = 0

    i = lai > 0
    z_OM[i], d_0[i] = res.calc_roughness(lai[i], height[i], height_width_ratio[i],
                                         classification[i], fractional_cover[i])
    
    band_data = [
            {'band_name': 'roughness_length', 'band_data': z_OM},
            {'band_name': 'zero_plane_displacement', 'band_data': d_0}
    ]

    su.write_snappy_product(output_file, band_data, 'aerodynamicRoughness', geo_coding)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
