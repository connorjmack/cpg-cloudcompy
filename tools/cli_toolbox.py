import cloudComPy as cc
import cloudComPy.M3C2
import sys
import os
import platform
import re
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
# Detect OS and set the "Root" of the mount
if platform.system() == "Darwin":  # Mac
    MOUNT_ROOT = Path("/Volumes/group")
else:  # Linux
    MOUNT_ROOT = Path("/project/group")

# Base Input Path
BASE_INPUT_DIR = MOUNT_ROOT / "LiDAR/LidarProcessing/LidarProcessingCliffs/results"

# Base Output Path
BASE_OUTPUT_DIR = MOUNT_ROOT / "LiDAR/LidarProcessing/LidarProcessingCliffs/cpg-cloudcompy/results"

# Available Locations (based on your prompt)
LOCATIONS = ["DelMar", "Solana", "Torrey", "SanElijo", "Encinitas", "Blacks"]

# Subfolder Types
TYPES = {
    "1": ("cropped", "cropped"),  # (folder_name, filename_suffix_indicator)
    "2": ("nobeach", "nobeach"),
    "3": ("noveg", "noveg")
}

def init_cc():
    if not cc.isInitialized():
        cc.initCC()

def get_user_input(prompt, default=None):
    text = f"{prompt} [{default}]: " if default else f"{prompt}: "
    val = input(text).strip()
    return val if val else default

def parse_date_from_filename(filename):
    """
    Extracts date from filename like '20170301_00590_...'
    Assumes YYYYMMDD is at the start.
    """
    match = re.match(r"(\d{8})_", filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d")
        except ValueError:
            return None
    return None

def find_surveys(location, type_key, start_date, end_date):
    """
    Finds and filters valid .las files based on location, type, and date range.
    """
    folder_name, suffix = TYPES[type_key]
    search_path = BASE_INPUT_DIR / location / folder_name
    
    if not search_path.exists():
        print(f"❌ Error: Path does not exist: {search_path}")
        return []

    print(f"🔍 Searching in: {search_path}")
    
    valid_files = []
    # Glob for .las files
    for f in search_path.glob("*.las"):
        # Double check it matches the 'type' (e.g. has 'nobeach' in name if required)
        if suffix not in f.name:
            continue
            
        f_date = parse_date_from_filename(f.name)
        if f_date and start_date <= f_date <= end_date:
            valid_files.append((f_date, f))
    
    # Sort by date
    valid_files.sort(key=lambda x: x[0])
    return [f[1] for f in valid_files]

def run_m3c2(cloud1, cloud2, output_dir):
    """Runs M3C2 between two Path objects."""
    print(f"   👉 {cloud1.name} \n      vs \n      {cloud2.name}")
    
    # Define Output Name
    # Extract Dates for cleaner filenames
    d1 = parse_date_from_filename(cloud1.name).strftime("%Y%m%d")
    d2 = parse_date_from_filename(cloud2.name).strftime("%Y%m%d")
    out_name = f"M3C2_{d1}_vs_{d2}.bin"
    out_path = output_dir / out_name

    if out_path.exists():
        print(f"      ⚠️ Skipping (Result exists): {out_name}")
        return

    try:
        # Load
        c1 = cc.loadPointCloud(str(cloud1))
        c2 = cc.loadPointCloud(str(cloud2))
        
        # M3C2 Params (Generic Guess)
        param_file = "params_temp.txt"
        cc.M3C2.M3C2guessParamsToFile(c1, c2, param_file)
        
        # Compute
        res = cc.M3C2.computeM3C2(c1, c2, param_file)
        
        if res:
            cc.SavePointCloud(c1, str(out_path))
            print(f"      ✅ Saved: {out_name}")
        else:
            print(f"      ❌ Failed to compute.")
            
    except Exception as e:
        print(f"      ❌ Error: {e}")

# --- MAIN WORKFLOW ---
def main():
    init_cc()
    print("\n🌊 --- CLIFF EROSION ANALYZER (LINUX/MAC) --- 🌊")
    print(f"📂 Reading from: {BASE_INPUT_DIR}")
    print(f"💾 Saving to:   {BASE_OUTPUT_DIR}\n")

    # 1. Select Location
    print("Available Locations:")
    for i, loc in enumerate(LOCATIONS):
        print(f"  [{i+1}] {loc}")
    loc_idx = int(get_user_input("Select Location #", "1")) - 1
    location = LOCATIONS[loc_idx]

    # 2. Select Data Type
    print("\nSelect Data Type:")
    print("  [1] Cropped (Raw Cliff)")
    print("  [2] No Beach (Beach Removed)")
    print("  [3] No Veg (Vegetation Removed)")
    type_key = get_user_input("Choice #", "3")

    # 3. Select Tool
    print("\nSelect Tool:")
    print("  [1] M3C2 (Distance/Erosion)")
    print("  [2] CANUPO (Classification - Placeholder)")
    tool_choice = get_user_input("Choice #", "1")
    
    # 4. Date Range
    print("\nDefine Date Range (Format: YYYY-MM):")
    start_str = get_user_input("Start Date", "2017-01")
    end_str = get_user_input("End Date", "2018-01")
    
    # Convert to datetime objects (start of month / end of month logic is simplified here to 1st of month)
    start_date = datetime.strptime(start_str, "%Y-%m")
    end_date = datetime.strptime(end_str, "%Y-%m")
    
    # 5. Find Files
    surveys = find_surveys(location, type_key, start_date, end_date)
    
    if len(surveys) < 2:
        print(f"\n❌ Not enough surveys found in range ({len(surveys)} found). Need at least 2.")
        return

    print(f"\n✅ Found {len(surveys)} surveys from {surveys[0].name[:8]} to {surveys[-1].name[:8]}")

    # 6. Comparison Mode
    print("\nComparison Mode:")
    print("  [1] Start vs. End (Total Change)")
    print("  [2] Sequential (Time Series: T1-T2, T2-T3...)")
    mode = get_user_input("Choice #", "2")

    # 7. Setup Output Directory
    tool_folder = "m3c2" if tool_choice == "1" else "canupo"
    # Create subfolder for this specific job to keep things clean? 
    # Let's put it in location/type/tool
    folder_name, _ = TYPES[type_key]
    final_output_dir = BASE_OUTPUT_DIR / tool_folder / location / folder_name
    final_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🚀 Starting Processing...")
    print(f"   Output Dir: {final_output_dir}")

    # 8. EXECUTE
    if tool_choice == "1": # M3C2
        if mode == "1": # Start vs End
            run_m3c2(surveys[0], surveys[-1], final_output_dir)
        else: # Sequential
            for i in range(len(surveys) - 1):
                run_m3c2(surveys[i], surveys[i+1], final_output_dir)
                
    elif tool_choice == "2": # CANUPO
        print("ℹ️ CANUPO batch processing logic would go here.")
        # Similar loop to load cloud, apply .prm file, save result.

if __name__ == "__main__":
    main()
