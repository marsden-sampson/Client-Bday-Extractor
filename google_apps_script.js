// Google Apps Script to import CSV data from a URL
// This script can be added to your Google Sheet for automatic data updates

function importBirthdayData() {
  // Replace with your actual CSV URL or use the manual import method
  const csvUrl = 'YOUR_CSV_URL_HERE';
  
  try {
    // Method 1: Import from URL (if you host the CSV file)
    const response = UrlFetchApp.fetch(csvUrl);
    const csvData = response.getContentText();
    const parsedData = Utilities.parseCsv(csvData);
    
    // Get the active sheet
    const sheet = SpreadsheetApp.getActiveSheet();
    
    // Clear existing data
    sheet.clear();
    
    // Add the parsed data
    if (parsedData.length > 0) {
      sheet.getRange(1, 1, parsedData.length, parsedData[0].length).setValues(parsedData);
      
      // Format the header row
      const headerRange = sheet.getRange(1, 1, 1, parsedData[0].length);
      headerRange.setFontWeight('bold');
      headerRange.setBackground('#e6f3ff');
      
      // Auto-resize columns
      sheet.autoResizeColumns(1, parsedData[0].length);
      
      Logger.log('Data imported successfully: ' + parsedData.length + ' rows');
    }
    
  } catch (error) {
    Logger.log('Error importing data: ' + error.toString());
  }
}

// Method 2: Manual data entry function (safer, no external dependencies)
function setupBirthdaySheet() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  // Set up headers
  const headers = ['Client Name', 'Birthday', 'Client Status'];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  // Format headers
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#e6f3ff');
  
  // Set column widths
  sheet.setColumnWidth(1, 200); // Client Name
  sheet.setColumnWidth(2, 120); // Birthday
  sheet.setColumnWidth(3, 120); // Client Status
  
  Logger.log('Birthday sheet setup complete');
}

// Method 3: Sort data by status priority
function sortByStatusPriority() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const dataRange = sheet.getDataRange();
  
  if (dataRange.getNumRows() <= 1) {
    Logger.log('No data to sort');
    return;
  }
  
  // Define sort order: Active, Dropout, NA
  const statusOrder = {'Active': 1, 'Dropout': 2, 'NA': 3};
  
  // Get all data including headers
  const data = dataRange.getValues();
  const headers = data[0];
  const dataRows = data.slice(1);
  
  // Find status column index
  const statusColumnIndex = headers.indexOf('Client Status');
  if (statusColumnIndex === -1) {
    Logger.log('Client Status column not found');
    return;
  }
  
  // Sort data rows
  dataRows.sort((a, b) => {
    const statusA = statusOrder[a[statusColumnIndex]] || 999;
    const statusB = statusOrder[b[statusColumnIndex]] || 999;
    
    if (statusA !== statusB) {
      return statusA - statusB;
    }
    
    // If same status, sort by name
    return a[0].toString().localeCompare(b[0].toString());
  });
  
  // Clear sheet and write sorted data
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (dataRows.length > 0) {
    sheet.getRange(2, 1, dataRows.length, headers.length).setValues(dataRows);
  }
  
  // Reformat headers
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#e6f3ff');
  
  Logger.log('Data sorted by status priority');
}