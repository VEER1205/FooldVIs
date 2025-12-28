import rasterio
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.vrt import WarpedVRT  # <--- THE MAGIC IMPORT
from rasterio.transform import Affine
from PIL import Image
import os

# ... keep imports ...

def process_flood_map(input_path, output_png_path):
    print(f"Processing {input_path} (Fast Mode)...")
    dst_crs = 'EPSG:4326'

    with rasterio.open(input_path) as src:
        with WarpedVRT(src, crs=dst_crs) as vrt:
            
            # 1. CALCULATE TRANSFORM
            transform, width, height = calculate_default_transform(
                vrt.crs, dst_crs, vrt.width, vrt.height, *vrt.bounds)
            
            # ⚡ SPEED FIX: DOWNSAMPLE
            # We limit the width to 800 pixels. Browser doesn't need more.
            # This makes it roughly 400x faster (20,000px -> 800px)
            MAX_WIDTH = 800
            scale_factor = MAX_WIDTH / width
            
            new_width = MAX_WIDTH
            new_height = int(height * scale_factor)
            
            new_transform = transform * Affine.scale(1/scale_factor, 1/scale_factor)
            
            kwargs = vrt.meta.copy()
            kwargs.update({
                'crs': dst_crs,
                'transform': new_transform,
                'width': new_width,
                'height': new_height,
                'count': 1,
                'dtype': 'float32'
            })

            destination = np.zeros((new_height, new_width), dtype=np.float32)

            # 2. REPROJECT (Fast)
            reproject(
                source=rasterio.band(vrt, 1),
                destination=destination,
                src_transform=vrt.transform,
                src_crs=vrt.crs,
                dst_transform=new_transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest)
            
            print(f"DEBUG: New Size: {new_width}x{new_height}")

            # 3. DETECT WATER
            water_threshold = 40
            flood_mask = np.where((destination < water_threshold) & (destination > 0), 255, 0).astype(np.uint8)

    
             # --- NEW: CALCULATE REAL AREA ---
            # 1 pixel in Sentinel-1 (GRD) is roughly 10m x 10m = 100 square meters
            pixel_count = np.count_nonzero(flood_mask)
            total_area_sq_meters = pixel_count * 100 
            total_area_km2 = total_area_sq_meters / 1_000_000
    
            print(f"🌊 REAL DETECTED AREA: {total_area_km2:.2f} km²")
            
            # 4. SAVE
            final_img = Image.fromarray(np.zeros((new_height, new_width, 4), dtype=np.uint8))
            datas = []
            for item in flood_mask.flatten():
                if item == 255:
                    datas.append((255, 0, 0, 200)) 
                else:
                    datas.append((0, 0, 0, 0)) 
            
            final_img.putdata(datas)
            final_img.save(output_png_path, "PNG")

            # 5. RETURN BOUNDS
            lon_min, lat_max = new_transform * (0, 0)
            lon_max, lat_min = new_transform * (new_width, new_height)
        return [[lat_max, lon_min], [lat_min, lon_max]]

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, "..", "data", "sentinel1_raw.tiff")
    output_file = os.path.join(current_dir, "..", "processed", "flood_mask.png")
    
    if not os.path.exists(input_file):
        print("❌ ERROR: File not found.")
    else:
        try:
            bounds = process_flood_map(input_file, output_file)
            print("✅ SUCCESS! Mask Generated.")
            print(f"Bounds: {bounds}") # Check if these look like GPS (e.g., 13.0, 80.0)
        except Exception as e:
            print(f"Error: {e}")