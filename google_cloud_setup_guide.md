# Google Cloud Setup Guide for Birthday Extraction App

## Step 1: Create Google Cloud Project (Free)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Click "Select a project" → "New Project"
4. Enter project name: "Birthday-Extraction-App"
5. Click "Create"

## Step 2: Enable Required APIs

1. In Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for "Google Sheets API" and click "Enable"
3. Search for "Google Drive API" and click "Enable"

## Step 3: Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Enter name: "birthday-app-service"
4. Enter description: "Service account for birthday extraction app"
5. Click "Create and Continue"
6. Skip role assignment (click "Continue")
7. Click "Done"

## Step 4: Generate Service Account Key

1. In Credentials page, find your service account
2. Click on the service account email
3. Go to "Keys" tab
4. Click "Add Key" → "Create New Key"
5. Select "JSON" format
6. Click "Create" - this downloads a JSON file

## Step 5: Copy JSON Contents

1. Open the downloaded JSON file in a text editor
2. Copy ALL the contents (entire JSON object)
3. Keep this safe - you'll paste it into the app

## Step 6: Share Google Sheet with Service Account

1. Open your Google Sheet
2. Click "Share" button
3. Add the service account email (looks like: birthday-app-service@your-project.iam.gserviceaccount.com)
4. Give "Editor" permissions
5. Click "Send"

## Step 7: Configure App

1. In the birthday extraction app sidebar, paste your JSON credentials
2. Enter your Google Sheets URL
3. Click "Update Google Sheets" after processing your PDF

## Important Notes

- Google Cloud free tier includes 100 requests per 100 seconds
- No payment method required for basic usage
- Keep your JSON credentials secure
- The service account email must have access to your Google Sheet

## Troubleshooting

**Error: "Credentials not found"**
- Make sure you pasted the complete JSON content
- Check that the JSON format is valid

**Error: "Permission denied"**
- Share your Google Sheet with the service account email
- Give "Editor" permissions

**Error: "API not enabled"**
- Ensure both Google Sheets API and Google Drive API are enabled
- Wait a few minutes after enabling APIs