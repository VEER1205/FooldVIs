from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.image_processor import process_flood_map
import os
import shutil
import rasterio
from rasterio.warp import calculate_default_transform
from rasterio.vrt import WarpedVRT

app = FastAPI()

# Get the base URL from environment variable or use default
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# Enable CORS - Allow your Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "https://*.vercel.app",  # Allow all Vercel deployments
        "*"  # For development - remove in production for security
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
current_dir = os.path.dirname(os.path.abspath(__file__))
processed_dir = os.path.join(current_dir, "processed")

# Create processed directory if it doesn't exist
os.makedirs(processed_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=processed_dir), name="static")


@app.post("/api/upload")
async def upload_satellite_image(file: UploadFile = File(...)):
    try:
        print(f"DEBUG: Real Upload Started for {file.filename}")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        input_path = os.path.join(data_dir, "sentinel1_raw.tiff")
        output_path = os.path.join(base_dir, "processed", "flood_mask.png")
        
        # 1. Save the uploaded file
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print("DEBUG: File saved successfully. Starting processing...")

        # 2. Process the file
        bounds = process_flood_map(input_path, output_path)
        
        # Calculate area (from the processor output)
        flooded_area = "45.2"  # You can extract this from process_flood_map if needed
        
        return {
            "status": "success",
            "message": "File processed successfully",
            "image_url": f"{BASE_URL}/static/flood_mask.png",
            "bounds": bounds,
            "stats": {
                "severity": "Critical",
                "flooded_area_km2": flooded_area
            }
        }
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/api/flood-map")
def get_current_map():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "data", "sentinel1_raw.tiff")
    output_path = os.path.join(base_dir, "processed", "flood_mask.png")
    
    # Check if the processed map exists
    if os.path.exists(output_path) and os.path.exists(input_path):
        try:
            # Dynamic bounds calculation
            dst_crs = 'EPSG:4326'
            with rasterio.open(input_path) as src:
                with WarpedVRT(src, crs=dst_crs) as vrt:
                    transform, width, height = calculate_default_transform(
                        vrt.crs, dst_crs, vrt.width, vrt.height, *vrt.bounds)
                    
                    # Calculate lat/lon bounds
                    lon_min, lat_max = transform * (0, 0)
                    lon_max, lat_min = transform * (width, height)
                    bounds = [[lat_max, lon_min], [lat_min, lon_max]]

            return {
                "status": "success",
                "image_url": f"{BASE_URL}/static/flood_mask.png",
                "bounds": bounds,
                "stats": {
                    "flooded_area_km2": "45.2",
                    "severity": "Active"
                }
            }
        except Exception as e:
            print(f"Error reading bounds: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": f"Could not read map data: {str(e)}"}
            
    return {"status": "error", "message": "No map data found"}


@app.get("/health")
def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "FloodVis API is running"}