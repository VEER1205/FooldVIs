from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.image_processor import process_flood_map
import os
import shutil

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
current_dir = os.path.dirname(os.path.abspath(__file__))
processed_dir = os.path.join(current_dir, "processed")
app.mount("/static", StaticFiles(directory=processed_dir), name="static")

# Don't forget to import shutil at the top!


@app.post("/api/upload")
async def upload_satellite_image(file: UploadFile = File(...)):
    try:
        print(f"DEBUG: Real Upload Started for {file.filename}")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        input_path = os.path.join(base_dir, "data", "sentinel1_raw.tiff")
        output_path = os.path.join(base_dir, "processed", "flood_mask.png")
        
        # --- THE REAL UPLOAD LOGIC ---
        # 1. Overwrite the existing file with the NEW one
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print("DEBUG: File saved successfully. Starting processing...")

        # 2. Process the NEW file
        # The WarpedVRT will automatically detect the new coordinates (e.g., New York, London)
        bounds = process_flood_map(input_path, output_path)
        
        return {
            "status": "success",
            "message": "File processed successfully",
            "image_url": "http://127.0.0.1:8000/static/flood_mask.png",
            "bounds": bounds,
            "stats": {
                "severity": "Unknown", # You can calculate this if you want
                "flooded_area_km2": "Calculating..." 
            }
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/flood-map")
def get_current_map():
    # This endpoint just returns the existing processed map (for page reloads)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, "processed", "flood_mask.png")
    
    if os.path.exists(output_path):
        # We need bounds. For hackathon speed, we can hardcode or re-calc.
        # Let's assume the frontend asks for the latest upload.
        return {
             "status": "success",
             "image_url": "http://127.0.0.1:8000/static/flood_mask.png",
             # You might want to store these bounds in a variable or file in a real app
             # For now, we return the last known good bounds
             "bounds": [[13.729, 76.107], [11.771, 78.718]], 
             "stats": { "flooded_area_km2": 45.2 }
        }
    return {"status": "error", "message": "No map data found"}