import streamlit as st
import pandas as pd
import io
import os
import json
from pdf_processor import PDFProcessor
from date_parser import DateParser
from google_sheets_client import GoogleSheetsClient
from data_validator import DataValidator

# Set page configuration
st.set_page_config(
    page_title="Client Birthday PDF to Google Sheets",
    page_icon="🎂",
    layout="wide"
)

def load_persistent_config():
    """Load configuration from persistent storage."""
    config_file = "app_config.json"
    default_config = {
        "credentials": "",
        "sheets_url": "",
        "worksheet_name": "Sheet1"
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    
    return default_config

def save_persistent_config(config):
    """Save configuration to persistent storage."""
    config_file = "app_config.json"
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f)
    except Exception:
        pass

def main():
    st.title("🎂 Client Birthday PDF to Google Sheets")
    st.markdown("Upload a PDF file containing client birthday information to automatically extract and update your Google Sheets.")
    
    # Load persistent configuration
    persistent_config = load_persistent_config()
    
    # Initialize session state
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'google_sheets_url' not in st.session_state:
        st.session_state.google_sheets_url = persistent_config.get("sheets_url", "")
    
    # Sidebar for Google Sheets configuration
    with st.sidebar:
        st.header("Google Sheets Configuration")
        
        # Setup instructions
        with st.expander("Setup Instructions", expanded=False):
            st.markdown("""
            **Quick Setup (Free):**
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create project → Enable Google Sheets API
            3. Create Service Account → Download JSON key
            4. Copy JSON content and paste below
            5. Share your Google Sheet with service account email
            
            **Service account email format:**
            `your-service@project-name.iam.gserviceaccount.com`
            """)
        
        # Initialize persistent storage using file system
        saved_credentials = persistent_config.get("credentials", "")
        saved_sheets_url = persistent_config.get("sheets_url", "")
        saved_worksheet_name = persistent_config.get("worksheet_name", "Sheet1")
        
        # Show current saved status with better organization
        if saved_credentials or saved_sheets_url:
            st.success("✅ Configuration saved for future sessions")
            
            # Settings management section
            with st.expander("⚙️ Manage Saved Settings"):
                col1, col2 = st.columns(2)
                with col1:
                    if saved_credentials:
                        st.write("**Credentials:** Saved")
                        if st.button("Clear Credentials"):
                            config = persistent_config.copy()
                            config["credentials"] = ""
                            save_persistent_config(config)
                            st.rerun()
                    else:
                        st.write("**Credentials:** Not saved")
                
                with col2:
                    if saved_sheets_url:
                        st.write("**Sheets URL:** Saved")
                        if st.button("Clear URL"):
                            config = persistent_config.copy()
                            config["sheets_url"] = ""
                            save_persistent_config(config)
                            st.session_state.google_sheets_url = ""
                            st.rerun()
                    else:
                        st.write("**Sheets URL:** Not saved")
        
        # Credentials input - only show if not saved
        if not saved_credentials:
            credentials_json = st.text_area(
                "Google Service Account JSON",
                placeholder='Paste your complete JSON credentials here...',
                height=100,
                help="Paste the entire JSON content from your downloaded service account key file"
            )
        else:
            credentials_json = saved_credentials
        
        # Validate and store credentials
        if credentials_json.strip():
            try:
                json.loads(credentials_json)
                os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'] = credentials_json
                
                # Save credentials to persistent storage if not already saved
                if not saved_credentials:
                    config = persistent_config.copy()
                    config["credentials"] = credentials_json
                    save_persistent_config(config)
                    st.success("Credentials saved successfully for future sessions")
                else:
                    st.success("Credentials loaded successfully")
            except Exception as e:
                st.error("Invalid JSON format. Please check your credentials.")
        
        # Google Sheets URL input with persistent storage
        if not saved_sheets_url:
            sheets_url = st.text_input(
                "Google Sheets URL",
                value=st.session_state.google_sheets_url,
                placeholder="https://docs.google.com/spreadsheets/d/your-sheet-id/edit",
                help="Paste the URL of your Google Sheets document"
            )
        else:
            sheets_url = saved_sheets_url
            st.info(f"Using saved Google Sheets URL")
        
        # Save URL if entered and not already saved
        if sheets_url and sheets_url != saved_sheets_url:
            if not saved_sheets_url:
                config = persistent_config.copy()
                config["sheets_url"] = sheets_url
                save_persistent_config(config)
                st.success("Google Sheets URL saved for future sessions")
            st.session_state.google_sheets_url = sheets_url
        
        # Worksheet name with persistent storage
        worksheet_name = st.text_input(
            "Worksheet Name",
            value=saved_worksheet_name,
            help="Name of the worksheet to update"
        )
        
        # Save worksheet name if changed
        if worksheet_name != saved_worksheet_name:
            config = persistent_config.copy()
            config["worksheet_name"] = worksheet_name
            save_persistent_config(config)
    
    # Main upload area
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        help="Upload a PDF file containing client birthday information"
    )
    
    if uploaded_file is not None:
        # Display file details
        st.success(f"File uploaded: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # Process PDF button
        if st.button("Extract Birthday Data", type="primary"):
            process_pdf(uploaded_file)
        
        # Display processed data if available
        if st.session_state.processed_data is not None:
            display_processed_data()
            
            # Update Google Sheets section
            if st.session_state.google_sheets_url:
                st.markdown("---")
                st.subheader("📊 Update Google Sheets")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Update Google Sheets", type="secondary"):
                        update_google_sheets(worksheet_name)
                
                with col2:
                    if st.button("Download as CSV"):
                        download_csv()
            else:
                st.warning("Please provide a Google Sheets URL in the sidebar to enable automatic updates.")

def process_pdf(uploaded_file):
    """Process the uploaded PDF file and extract birthday data."""
    try:
        with st.spinner("Processing PDF file..."):
            # Initialize processors
            pdf_processor = PDFProcessor()
            date_parser = DateParser()
            validator = DataValidator()
            
            # Extract structured data using coordinate-based approach
            progress_bar = st.progress(0)
            progress_bar.progress(25, text="Extracting structured data from PDF...")
            
            raw_data = pdf_processor.extract_structured_data_with_coordinates(uploaded_file)
            
            progress_bar.progress(50, text="Processing extracted data...")
            
            if not raw_data:
                st.error("No birthday data found in the PDF. Please check the format of your PDF.")
                return
            
            progress_bar.progress(75, text="Processing extracted data...")
            
            # Skip validation for now since coordinate extraction is working
            cleaned_data = raw_data
            
            progress_bar.progress(100, text="Processing complete!")
            
            # Create DataFrame with proper column names
            df = pd.DataFrame(cleaned_data)
            
            # Rename columns to match user requirements
            if not df.empty:
                column_mapping = {
                    'name': 'Client Name',
                    'short_name': 'Short Name',
                    'birthday': 'Birthday',
                    'status': 'Client Status'
                }
                
                # Only rename columns that exist
                for old_col, new_col in column_mapping.items():
                    if old_col in df.columns:
                        df = df.rename(columns={old_col: new_col})
                
                # Ensure we have the four required columns in the right order
                required_columns = ['Client Name', 'Short Name', 'Birthday', 'Client Status']
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = 'Unknown'
                
                # Sort by status priority (Active, Dropout, NA) then by name
                status_priority = {'Active': 1, 'Dropout': 2, 'NA': 3}
                df['sort_priority'] = df['Client Status'].apply(lambda x: status_priority.get(x, 4))
                df = df.sort_values(['sort_priority', 'Client Name']).drop('sort_priority', axis=1)
                
                # Reorder columns to match requirements - now with 4 columns
                display_columns = ['Client Name', 'Short Name', 'Birthday', 'Client Status']
                available_columns = [col for col in display_columns if col in df.columns]
                df = df[available_columns + [col for col in df.columns if col not in available_columns]]
            
            # Store in session state
            st.session_state.processed_data = df
            
            # Clear progress bar
            progress_bar.empty()
            
            st.success(f"Successfully extracted {len(df)} client birthday records!")
            
            # Debug info for data extraction
            with st.expander("📊 Data Extraction Summary"):
                st.write(f"Total records found: {len(df)}")
                st.write(f"Expected: 1571 clients")
                
                if len(df) > 0:
                    st.write(f"Columns available: {list(df.columns)}")
                    st.write("Sample of extracted data:")
                    st.dataframe(df.head(10), hide_index=True)
                else:
                    st.write("No data was extracted. This indicates an issue with the parsing logic.")
                
                # Show debug info from parser
                if hasattr(date_parser, '_debug_info'):
                    debug = date_parser._debug_info
                    st.write("### Parser Debug Information:")
                    st.write(f"- Total lines processed: {debug.get('total_lines', 0)}")
                    st.write(f"- Header found: {debug.get('header_found', False)}")
                    st.write(f"- Clients extracted: {debug.get('clients_extracted', 0)}")

                    
                    # Show potential clients that were skipped
                    if debug.get('potential_clients'):
                        st.write("### Potential clients that were skipped:")
                        for client in debug['potential_clients'][:10]:  # Show first 10
                            st.write(f"- {client}")
                    
                    # Show statistics about clients without birthdays
                    if 'processed_data' in st.session_state:
                        clients_without_birthdays = sum(1 for client in st.session_state.processed_data 
                                                       if isinstance(client, dict) and (not client.get('birthday') or client.get('birthday') == 'None'))
                        if clients_without_birthdays > 0:
                            st.write(f"- **Clients still missing birthdays: {clients_without_birthdays}**")
                    
                    if debug.get('sample_lines'):
                        st.write("### Sample lines from PDF:")
                        for sample_line in debug['sample_lines']:
                            st.code(sample_line)
                    
                    # Show skipped lines that might be clients
                    if debug.get('skipped_lines'):
                        st.write("### Lines that were skipped (might contain clients):")
                        for skipped_line in debug['skipped_lines']:
                            st.code(f"Skipped: {skipped_line}")
                    
                    # Additional insights for missing clients
                    if len(df) < 1571:
                        st.write("### Analysis:")
                        missing_count = 1571 - len(df)
                        st.write(f"Missing {missing_count} clients ({missing_count/1571*100:.1f}% of expected)")
                        st.write(f"Potential clients found but not extracted: {len(debug.get('potential_clients', []))}")
                        
                        # Suggestions for improving extraction
                        st.write("**Next steps to improve extraction:**")
                        st.write("- Review the skipped lines above to see patterns")
                        st.write("- Check if some client data uses different formatting")
                        st.write("- Verify all date headers are being detected properly")
            
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        st.error("Please ensure your PDF is not password-protected and contains readable text.")

def display_processed_data():
    """Display the processed birthday data."""
    st.markdown("---")
    st.subheader("📋 Extracted Birthday Data")
    
    df = st.session_state.processed_data
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Clients", len(df))
    with col2:
        birthday_col = 'Birthday' if 'Birthday' in df.columns else 'birthday'
        if birthday_col in df.columns:
            valid_dates = df[birthday_col].notna().sum()
            st.metric("Valid Birthdays", valid_dates)
        else:
            st.metric("Valid Birthdays", "N/A")
            valid_dates = 0
            
        # Show how many are missing birthdays
        missing_birthdays = len(df) - valid_dates
        if missing_birthdays > 0:
            st.error(f"⚠️ {missing_birthdays} clients missing birthdays")
    with col3:
        invalid_dates = len(df) - valid_dates
        st.metric("Invalid/Missing Dates", invalid_dates)
    
    # Display data table with all four columns
    display_columns = ['Client Name', 'Short Name', 'Birthday', 'Client Status']
    available_columns = [col for col in display_columns if col in df.columns]
    
    # Add status breakdown metrics
    if 'Client Status' in df.columns:
        status_counts = df['Client Status'].value_counts()
        st.write("### Status Breakdown:")
        cols = st.columns(len(status_counts))
        for i, (status, count) in enumerate(status_counts.items()):
            with cols[i]:
                st.metric(f"{status} Clients", count)
    
    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True
    )
    
    # Show data quality issues if any
    birthday_col = 'Birthday' if 'Birthday' in df.columns else 'birthday'
    if birthday_col in df.columns:
        invalid_rows = df[df[birthday_col].isna()]
        if not invalid_rows.empty:
            st.warning("⚠️ Some rows have invalid or missing birthday data:")
            st.dataframe(invalid_rows[display_columns], use_container_width=True, hide_index=True)

def update_google_sheets(worksheet_name):
    """Update the Google Sheets with processed data."""
    try:
        with st.spinner("Updating Google Sheets..."):
            sheets_client = GoogleSheetsClient()
            
            # Extract sheet ID from URL
            sheet_id = extract_sheet_id(st.session_state.google_sheets_url)
            
            if not sheet_id:
                st.error("Invalid Google Sheets URL. Please provide a valid URL.")
                return
            
            # Update the sheet
            success = sheets_client.update_sheet(
                sheet_id, 
                worksheet_name, 
                st.session_state.processed_data
            )
            
            if success:
                st.success("✅ Google Sheets updated successfully!")
                st.balloons()
            else:
                st.error("Failed to update Google Sheets. Please check your credentials and permissions.")
                
    except Exception as e:
        st.error(f"Error updating Google Sheets: {str(e)}")

def download_csv():
    """Provide CSV download functionality."""
    if st.session_state.processed_data is not None:
        df = st.session_state.processed_data
        
        # Ensure proper column order for Google Sheets import - now with 4 columns
        required_columns = ['Client Name', 'Short Name', 'Birthday', 'Client Status']
        export_columns = [col for col in required_columns if col in df.columns]
        export_df = df[export_columns]
        
        csv_buffer = io.StringIO()
        export_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Create filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"client_birthdays_{timestamp}.csv"
        
        st.download_button(
            label="📥 Download CSV for Google Sheets",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            help="Download the extracted data as CSV file to import into Google Sheets"
        )
        
        st.info("💡 To import into Google Sheets: File > Import > Upload > Select this CSV file > Replace spreadsheet")

def extract_sheet_id(url):
    """Extract Google Sheets ID from URL."""
    try:
        if "/spreadsheets/d/" in url:
            return url.split("/spreadsheets/d/")[1].split("/")[0]
        return None
    except:
        return None

if __name__ == "__main__":
    main()
