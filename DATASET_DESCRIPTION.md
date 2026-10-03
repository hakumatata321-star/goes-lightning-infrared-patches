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

## Licence

NOAA GOES data are works of the U.S. Government and are in the public domain in the United States. This compilation is released under CC0 1.0.
