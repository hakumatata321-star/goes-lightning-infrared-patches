# GOES-16 / GOES-18 Infrared Patches with GLM Lightning Flash Counts

## Overview

This dataset pairs real geostationary infrared imagery with real lightning observations from NOAA's GOES-16 (GOES-East, 75.2 W) and GOES-18 (GOES-West, 137.2 W) satellites. Each record is a 128 by 128 pixel patch (about 256 km across) observed in four infrared bands at four consecutive five-minute scans. The record also holds the number of lightning flashes the Geostationary Lightning Mapper (GLM) recorded in each 4 by 4 pixel cell during each of the three intervals between the scans. Nothing in the dataset is simulated or generated: every value comes from an operational NOAA product.

## Source

- ABI L2 Cloud and Moisture Imagery, CONUS sector (`ABI-L2-CMIPC`), channels 8, 10, 13 and 15, as brightness temperature in kelvin at 2 km nominal resolution.
- GLM L2 Lightning Cluster Filter Algorithm (`GLM-L2-LCFA`), flash-level records with `flash_quality_flag == 0`.
- Both products were read from the public NOAA Open Data Dissemination buckets `noaa-goes16` and `noaa-goes18` on AWS (https://registry.opendata.aws/noaa-goes/), for days of year 183 to 224 of 2024 (1 July to 11 August), 18:00 to 24:00 UTC.

## How the patches were built

1. For each day, scan start times having all four channels were grouped into windows of four consecutive scans, no more than 16 minutes apart. Consecutive windows share their boundary scan.
2. Each GLM flash was placed by its first-event time and its latitude and longitude. It was projected with the satellite's own fixed-grid geostationary projection onto the ABI pixel grid. It was counted in the 4 by 4 pixel cell and the inter-scan interval it fell into, using the scan mid-times as interval bounds.
3. In each window, up to 12 patch positions were drawn around cells with flashes, with a random offset of up to 8 cells, and 6 at random positions. Patches overlapping an already accepted patch of the same window, and patches with any missing pixel, were dropped.
4. Each patch was given a keyed identifier that reveals nothing about its date or position, and its approximate local solar hour was kept.

The builder script `build_patches.py` in the repository reproduces steps 1 to 3 from the NOAA buckets.

## Contents

- `patches.csv`: one row per patch, with `patch_id`, `split` (train, test or unlabelled), `satellite` and `local_hour`.
- `goes16_patches.npz`: arrays `patch_id`, `inputs` (N, 4, 4, 128, 128) float16 and `flash_counts` (N, 3, 32, 32) uint16.
- `goes18_patches.npz`: the same arrays for GOES-18.
- `build_patches.py`: the builder script.
- `LICENSE`: terms.

Axes of `inputs`: scan (oldest first), channel (8, 10, 13, 15), row, column. Axes of `flash_counts`: interval, row, column. Cell (r, c) covers pixel rows 4r to 4r+3 and columns 4c to 4c+3.

Split design: 3,000 GOES-16 patches from days 183 to 202 form the training split. Up to 1,100 GOES-18 patches from days 214 to 219 form the test split. GOES-18 patches from days 222 to 224 form the unlabelled split. No calendar day is shared between splits.

## Intended Use

The dataset is meant for research and benchmarking on mapping lightning activity from infrared imagery, and on transferring such models from one geostationary satellite to another (GOES-16 to GOES-18). It also suits teaching about satellite meteorology and spatial verification with the Fractions Skill Score. It is not intended for operational warnings or safety decisions.

## Known Limitations

- Coverage is limited to the CONUS sector of each satellite (the contiguous United States and nearby ocean), to 42 summer days of 2024 (1 July to 11 August), and to 18:00 to 24:00 UTC. Other seasons, night-time storms, the tropics and the Southern Hemisphere are not represented.
- GLM does not see every flash. Its detection efficiency is lower in daytime than at night, lower towards the edge of its field of view, and lower for flashes deep inside thick cloud. Flashes with a non-zero quality flag were dropped. The counts are therefore a lower bound on true lightning.
- No parallax correction was applied. GLM flash positions and ABI cloud-top pixels are located on slightly different reference surfaces, so tall storms far from the sub-satellite point can be offset by a few kilometres, up to about one grid cell.
- The interval bounds use the mid-scan time of channel 13 for all four channels. Each channel of a scan is taken a few seconds apart, and a flash near a bound may fall into the neighbouring interval.
- Patch positions oversample lightning: 12 of the 18 candidate positions in each window are drawn near flashes. The share of patches with lightning is therefore far higher than in a random sample of the sky.
- Brightness temperatures are stored as float16, a step of 0.125 to 0.25 K in the range of the data.
- GOES-16 and GOES-18 differ in viewing angle, climate regime and calibration, and only a few days of each are included. Results may not carry over to other satellites or years.

## Licence

NOAA GOES data are works of the U.S. Government and are in the public domain in the United States. This compilation is released under CC0 1.0.
