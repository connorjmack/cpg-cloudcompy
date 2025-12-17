import streamlit as st
import cloudComPy as cc
import cloudComPy.M3C2
import cloudComPy.Canupo
import os
import tempfile
from pathlib import Path

# --- 1. Initialization ---
# Initialize CloudCompare (required before calling plugins)
if not cc.isInitialized():
    cc.initCC()

st.set_page_config(page_title="CloudComPy Lab Toolbox", layout="wide")
st.title("☁️ Point Cloud Processing Toolbox")

# --- 2. Helper Functions ---
def save_uploaded_file(uploaded_file):
    """Save Streamlit upload to a temp file and return the path."""
    try:
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

# --- 3. Sidebar: Data Loading ---
st.sidebar.header("1. Input Data")
uploaded_cloud_1 = st.sidebar.file_uploader("Upload Cloud #1 (Reference/Source)", type=["las", "laz", "xyz", "bin"])
uploaded_cloud_2 = st.sidebar.file_uploader("Upload Cloud #2 (Comparison/Core)", type=["las", "laz", "xyz", "bin"])

# Session state to hold loaded cloud paths to avoid re-uploading
if 'cloud1_path' not in st.session_state: st.session_state['cloud1_path'] = None
if 'cloud2_path' not in st.session_state: st.session_state['cloud2_path'] = None

if uploaded_cloud_1:
    st.session_state['cloud1_path'] = save_uploaded_file(uploaded_cloud_1)
if uploaded_cloud_2:
    st.session_state['cloud2_path'] = save_uploaded_file(uploaded_cloud_2)

# --- 4. Main Interface ---
tab_m3c2, tab_canupo, tab_results = st.tabs(["📏 M3C2 Distance", "🌲 CANUPO Classification", "💾 Results"])

# === TAB 1: M3C2 ===
with tab_m3c2:
    st.header("M3C2 Distance Calculation")
    
    if not (st.session_state['cloud1_path'] and st.session_state['cloud2_path']):
        st.warning("Please upload two point clouds in the sidebar to use M3C2.")
    else:
        # M3C2 Parameters
        col1, col2 = st.columns(2)
        with col1:
            scales = st.text_input("Scales (e.g., 0.5;1.0)", "0.5")
            subsampling = st.number_input("Subsampling Radius", value=0.1)
        with col2:
            max_depth = st.number_input("Max Search Depth", value=5.0)
            use_precision = st.checkbox("Use Precision Maps", value=False)

        if st.button("Run M3C2"):
            with st.spinner("Calculating M3C2 Distances... This may take a while."):
                try:
                    # 1. Load Clouds
                    cloud1 = cc.loadPointCloud(st.session_state['cloud1_path'])
                    cloud2 = cc.loadPointCloud(st.session_state['cloud2_path'])
                    
                    # 2. Setup M3C2 Parameters
                    # M3C2 in cloudComPy often reads params from a file. 
                    # We can use the helper to guess/write params.
                    param_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt").name
                    
                    # This helper creates a default param file we can modify or use
                    cc.M3C2.M3C2guessParamsToFile(cloud1, cloud2, param_file)
                    
                    # 3. Run Compute
                    # Note: exact signature depends on the wrapper version, referencing `computeM3C2`
                    result = cc.M3C2.computeM3C2(cloud1, cloud2, param_file)
                    
                    if result:
                        st.success("M3C2 Computation Successful!")
                        # Save result for download
                        res_path = tempfile.NamedTemporaryFile(delete=False, suffix=".bin").name
                        cc.SavePointCloud(cloud1, res_path) # The result is usually stored as an SF on cloud1
                        st.session_state['last_result'] = res_path
                    else:
                        st.error("M3C2 failed. Check console logs.")
                        
                except Exception as e:
                    st.error(f"Execution Error: {e}")

# === TAB 2: CANUPO ===
with tab_canupo:
    st.header("CANUPO Classification")
    
    # Upload Classifier
    uploaded_classifier = st.file_uploader("Upload CANUPO Classifier (.prm)", type=["prm"])
    
    if st.button("Run Classification"):
        if not st.session_state['cloud1_path']:
            st.error("Please upload Cloud #1 in the sidebar.")
        elif not uploaded_classifier:
            st.error("Please upload a .prm classifier file.")
        else:
            with st.spinner("Classifying..."):
                try:
                    # Load Resources
                    cloud = cc.loadPointCloud(st.session_state['cloud1_path'])
                    classifier_path = save_uploaded_file(uploaded_classifier)
                    
                    # Run Classify (Referring to ClassifyPy binding)
                    # Arguments: cloud, classifier file, (optional core points), ...
                    cc.Canupo.Classify(cloud, classifier_path)
                    
                    st.success("Classification done!")
                    
                    # Save Output
                    out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".bin").name
                    cc.SavePointCloud(cloud, out_path)
                    st.session_state['last_result'] = out_path
                    
                except Exception as e:
                    st.error(f"CANUPO Error: {e}")

# === TAB 3: RESULTS ===
with tab_results:
    st.header("Download Processed Data")
    if 'last_result' in st.session_state and st.session_state['last_result']:
        with open(st.session_state['last_result'], "rb") as f:
            st.download_button(
                label="Download Result Cloud (.bin)",
                data=f,
                file_name="processed_cloud.bin",
                mime="application/octet-stream"
            )
    else:
        st.info("No results generated yet.")
