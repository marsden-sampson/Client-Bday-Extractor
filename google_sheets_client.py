import os
import json
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
import streamlit as st

class GoogleSheetsClient:
    """Handles Google Sheets API operations."""
    
    def __init__(self):
        self.service = None
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Sheets service with credentials."""
        try:
            # Try to get credentials from environment variables
            creds = self._get_credentials()
            
            if creds:
                self.service = build('sheets', 'v4', credentials=creds)
            else:
                st.error("Google Sheets credentials not found. Please set up your credentials.")
                
        except Exception as e:
            st.error(f"Failed to initialize Google Sheets service: {str(e)}")
    
    def _get_credentials(self):
        """Get Google API credentials from environment variables."""
        try:
            # Try service account credentials first
            service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            if service_account_info:
                try:
                    # Parse JSON string
                    service_account_dict = json.loads(service_account_info)
                    creds = ServiceAccountCredentials.from_service_account_info(
                        service_account_dict, scopes=self.scopes
                    )
                    return creds
                except json.JSONDecodeError:
                    st.error("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON environment variable")
            
            # Try individual credential components
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            refresh_token = os.getenv('GOOGLE_REFRESH_TOKEN')
            
            if all([client_id, client_secret, refresh_token]):
                creds = Credentials(
                    None,  # token
                    refresh_token=refresh_token,
                    id_token=None,
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=self.scopes
                )
                return creds
            
            return None
            
        except Exception as e:
            st.error(f"Error getting credentials: {str(e)}")
            return None
    
    def update_sheet(self, spreadsheet_id, worksheet_name, dataframe, retry_count=3):
        """
        Update Google Sheets with DataFrame data.
        
        Args:
            spreadsheet_id (str): Google Sheets ID
            worksheet_name (str): Name of the worksheet
            dataframe (pd.DataFrame): Data to upload
            retry_count (int): Number of retry attempts
            
        Returns:
            bool: Success status
        """
        if not self.service:
            st.error("Google Sheets service not initialized")
            return False
        
        try:
            # Prepare data for Google Sheets
            values = self._prepare_data_for_sheets(dataframe)
            
            # Clear existing data first
            self._clear_sheet_data(spreadsheet_id, worksheet_name)
            
            # Update with new data
            range_name = f"{worksheet_name}!A1"
            
            body = {
                'values': values,
                'majorDimension': 'ROWS'
            }
            
            for attempt in range(retry_count):
                try:
                    result = self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body=body
                    ).execute()
                    
                    updated_rows = result.get('updatedRows', 0)
                    st.success(f"Successfully updated {updated_rows} rows in Google Sheets")
                    
                    # Format the sheet and add dropdowns
                    self._format_sheet(spreadsheet_id, worksheet_name, len(values), len(values[0]) if values else 0)
                    self._add_data_validation(spreadsheet_id, worksheet_name, len(values))
                    
                    return True
                    
                except HttpError as e:
                    if attempt < retry_count - 1:
                        st.warning(f"Attempt {attempt + 1} failed, retrying...")
                        continue
                    else:
                        st.error(f"Failed to update sheet after {retry_count} attempts: {str(e)}")
                        return False
                        
        except Exception as e:
            st.error(f"Error updating Google Sheets: {str(e)}")
            return False
    
    def _prepare_data_for_sheets(self, dataframe):
        """Prepare DataFrame data for Google Sheets format."""
        # Convert DataFrame to list of lists
        values = []
        
        # Add headers
        headers = list(dataframe.columns)
        values.append(headers)
        
        # Add data rows
        for _, row in dataframe.iterrows():
            row_values = []
            for col in headers:
                value = row[col]
                
                # Handle different data types
                if pd.isna(value):
                    row_values.append('')
                elif isinstance(value, (int, float)):
                    row_values.append(str(value))
                else:
                    row_values.append(str(value))
            
            values.append(row_values)
        
        return values
    
    def _clear_sheet_data(self, spreadsheet_id, worksheet_name):
        """Clear existing data from the worksheet."""
        try:
            # Get sheet properties to determine range
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            # Find the worksheet
            worksheet_id = None
            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == worksheet_name:
                    worksheet_id = sheet['properties']['sheetId']
                    break
            
            if worksheet_id is None:
                # Create the worksheet if it doesn't exist
                self._create_worksheet(spreadsheet_id, worksheet_name)
                return
            
            # Clear the sheet
            range_name = f"{worksheet_name}!A:Z"
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                body={}
            ).execute()
            
        except Exception as e:
            st.warning(f"Could not clear existing data: {str(e)}")
    
    def _create_worksheet(self, spreadsheet_id, worksheet_name):
        """Create a new worksheet if it doesn't exist."""
        try:
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': worksheet_name
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            st.info(f"Created new worksheet: {worksheet_name}")
            
        except Exception as e:
            st.warning(f"Could not create worksheet: {str(e)}")
    
    def _format_sheet(self, spreadsheet_id, worksheet_name, num_rows, num_cols):
        """Apply basic formatting to the sheet."""
        try:
            # Get worksheet ID
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            worksheet_id = None
            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == worksheet_name:
                    worksheet_id = sheet['properties']['sheetId']
                    break
            
            if worksheet_id is None:
                return
            
            # Format header row
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': worksheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': num_cols
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 0.9,
                                'blue': 0.9
                            },
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]
            
            # Auto-resize columns
            requests.append({
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': worksheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': num_cols
                    }
                }
            })
            
            body = {'requests': requests}
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
        except Exception as e:
            st.warning(f"Could not format sheet: {str(e)}")
    
    def _add_data_validation(self, spreadsheet_id, worksheet_name, num_rows):
        """Add dropdown validation for Client Status column."""
        try:
            # Get worksheet ID
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            worksheet_id = None
            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == worksheet_name:
                    worksheet_id = sheet['properties']['sheetId']
                    break
            
            if worksheet_id is None:
                return
            
            # Find Client Status column (typically column D - index 3)
            status_column_index = 3  # Column D (0-indexed)
            
            # Create data validation for Client Status column
            requests = [{
                'setDataValidation': {
                    'range': {
                        'sheetId': worksheet_id,
                        'startRowIndex': 1,  # Skip header row
                        'endRowIndex': num_rows,
                        'startColumnIndex': status_column_index,
                        'endColumnIndex': status_column_index + 1
                    },
                    'rule': {
                        'condition': {
                            'type': 'ONE_OF_LIST',
                            'values': [
                                {'userEnteredValue': 'Active'},
                                {'userEnteredValue': 'Dropout'},
                                {'userEnteredValue': 'NA'}
                            ]
                        },
                        'showCustomUi': True,
                        'strict': True
                    }
                }
            }]
            
            body = {'requests': requests}
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            st.success("Added dropdown validation for Client Status column")
            
        except Exception as e:
            st.warning(f"Could not add data validation: {str(e)}")
    
    def test_connection(self, spreadsheet_id):
        """Test connection to Google Sheets."""
        try:
            if not self.service:
                return False, "Service not initialized"
            
            # Try to get spreadsheet metadata
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            title = result.get('properties', {}).get('title', 'Unknown')
            return True, f"Successfully connected to: {title}"
            
        except HttpError as e:
            return False, f"HTTP Error: {str(e)}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
