import rasterio
import numpy as np
import os

# Point this to your RAW tiff file
input_file = "backend/data/sentinel1_raw.tiff"

if os.path.exists(input_file):
    with rasterio.open(input_file) as src:
        data = src.read(1)
        print(f"Min Value: {np.min(data)}")
        print(f"Max Value: {np.max(data)}")
        print(f"Average Value: {np.mean(data)}")
        print("--------------------------------")
        print("💡 TIP: Set your 'water_threshold' to be slightly higher than the 'Min Value'.")
else:
    print("File not found.")