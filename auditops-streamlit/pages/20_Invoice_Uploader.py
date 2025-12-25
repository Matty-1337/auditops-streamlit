"""
Invoice Uploader Page
Handles invoice file uploads and processing for different vendors.
"""
import streamlit as st
import pandas as pd
from io import BytesIO
import sys
import os

# Add parent directory to path to import invoice_engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from invoice_engine import InvoiceIngester
except ImportError:
    st.error("Error importing invoice_engine module. Please ensure invoice_engine.py is in the project root.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Invoice Uploader",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Invoice Uploader")
st.markdown("---")

# Initialize session state for processed data
if 'invoice_result_df' not in st.session_state:
    st.session_state.invoice_result_df = None

# Sidebar configuration
with st.sidebar:
    st.header("Invoice Processing")
    st.markdown("---")
    
    # Vendor selection dropdown
    vendor_options = [
        "Fintech Export (CSV)",
        "Spec's (PDF)",
        "Wolf Express (PDF)"
    ]
    
    selected_vendor = st.selectbox(
        "Select Vendor:",
        options=vendor_options,
        help="Choose the vendor/source of the invoice file"
    )
    
    st.markdown("---")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload Invoice File:",
        type=['csv', 'pdf'],
        help="Upload a CSV file for Fintech Export, or PDF for other vendors"
    )
    
    st.markdown("---")
    
    # Vendor master file path configuration (for PDF processing)
    if selected_vendor in ["Spec's (PDF)", "Wolf Express (PDF)"]:
        st.info("📌 PDF Processing requires a vendor master file for product matching.")
        vendor_master_path = st.text_input(
            "Vendor Master File Path:",
            value="data/master_files/specs_master.csv" if selected_vendor == "Spec's (PDF)" else "data/master_files/wolf_master.csv",
            help="Path to the vendor master CSV file"
        )
    else:
        vendor_master_path = None

# Main content area
if uploaded_file is not None:
    # Validate file type matches vendor selection
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    if selected_vendor == "Fintech Export (CSV)" and file_extension != 'csv':
        st.error("❌ Invalid file type. Please upload a CSV file for Fintech Export.")
    elif selected_vendor in ["Spec's (PDF)", "Wolf Express (PDF)"] and file_extension != 'pdf':
        st.error("❌ Invalid file type. Please upload a PDF file for PDF vendors.")
    else:
        # Process button
        if st.button("🔄 Process Invoice", type="primary", use_container_width=True):
            try:
                # Initialize ingester
                ingester = InvoiceIngester()
                
                with st.spinner("Processing invoice file..."):
                    # Process based on vendor type
                    if selected_vendor == "Fintech Export (CSV)":
                        # Fast Lane: Process CSV
                        result_df = ingester.process_fintech_csv(uploaded_file)
                        st.session_state.invoice_result_df = result_df
                        st.success(f"✅ Successfully processed {len(result_df)} rows from Fintech CSV!")
                    
                    else:
                        # Smart Lane: Process PDF
                        if not vendor_master_path:
                            st.error("❌ Vendor master file path is required for PDF processing.")
                        else:
                            # Check if master file exists
                            if not os.path.exists(vendor_master_path):
                                st.warning(f"⚠️ Vendor master file not found at: {vendor_master_path}")
                                st.info("💡 Using default path. Please ensure the master file exists.")
                            
                            # Read file content into BytesIO for processing
                            file_content = BytesIO(uploaded_file.read())
                            file_content.seek(0)  # Reset pointer to beginning
                            
                            result_df = ingester.process_pdf_invoice(
                                file_content,
                                vendor_master_file_path=vendor_master_path
                            )
                            st.session_state.invoice_result_df = result_df
                            
                            # Count matches
                            match_count = len([x for x in result_df.get('Matched Internal ID', []) if x != 'No Match'])
                            st.success(
                                f"✅ Successfully processed PDF invoice: {len(result_df)} items, "
                                f"{match_count} products matched!"
                            )
            
            except ValueError as e:
                st.error(f"❌ Validation Error: {str(e)}")
            except FileNotFoundError as e:
                st.error(f"❌ File Not Found: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error processing invoice: {str(e)}")
                st.exception(e)
        
        # Display results if available
        if st.session_state.invoice_result_df is not None:
            st.markdown("---")
            st.header("📊 Processed Invoice Data")
            
            result_df = st.session_state.invoice_result_df
            
            # Display dataframe
            st.dataframe(
                result_df,
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            
            # Download button
            csv_data = result_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Processed Data (CSV)",
                data=csv_data,
                file_name=f"processed_invoice_{selected_vendor.replace(' ', '_').replace('(', '').replace(')', '')}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
            
            # Statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", len(result_df))
            
            if 'Matched Internal ID' in result_df.columns:
                match_count = len([x for x in result_df['Matched Internal ID'] if x != 'No Match'])
                match_rate = (match_count / len(result_df) * 100) if len(result_df) > 0 else 0
                with col2:
                    st.metric("Matched Products", match_count)
                with col3:
                    st.metric("Match Rate", f"{match_rate:.1f}%")
else:
    # Instructions when no file is uploaded
    st.info("👈 Please select a vendor and upload an invoice file using the sidebar.")
    
    st.markdown("---")
    st.subheader("📖 How to Use")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Fast Lane (Fintech CSV):**
        1. Select "Fintech Export (CSV)" from dropdown
        2. Upload a CSV file
        3. Click "Process Invoice"
        4. Download the cleaned data
        """)
    
    with col2:
        st.markdown("""
        **Smart Lane (PDF):**
        1. Select a PDF vendor (Spec's or Wolf Express)
        2. Ensure vendor master file path is correct
        3. Upload a PDF invoice file
        4. Click "Process Invoice"
        5. Review matched products and download
        """)
    
    st.markdown("---")
    st.markdown("""
    **Note:** For PDF processing, the system will:
    - Extract invoice header (Invoice #, Date)
    - Extract product table (SKU, Description, Qty, Price)
    - Normalize product sizes for comparison
    - Match products against vendor master file using fuzzy matching
    - Return extracted data with matched internal IDs
    """)

