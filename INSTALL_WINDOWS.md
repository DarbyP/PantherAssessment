# Windows Installation Instructions

## Download

1. Go to the [latest release](../../releases/latest)
2. Download `PantherAssessment-Windows.zip`
3. Extract the ZIP file to a location of your choice

## First Launch

Windows SmartScreen will prevent the application from running initially because it's not code-signed.

1. Double-click `PantherAssessment.exe`
2. Windows SmartScreen will show "Windows protected your PC"
3. Click **"More info"**
4. Click **"Run anyway"**

This warning will only appear the first time you run the application.

## Initial Setup and Authentication
When you first launch Panther Assessment, you will be prompted to authenticate with Canvas. Follow these steps:
1.	Enter your university’s Canvas url. Be sure you enter the direct URL (e.g., https://university.instructure.com) rather than a redirect URL (https://canvas.university.edu).
2.	After entering the Canvas URL, the Canvas authentication window will open 
3.	Click the "Open Canvas" button to visit Canvas in your browser
4.	In Canvas, go to Account → Settings → Approved Integrations
5.	Click "+ New Access Token"
6.	Enter a purpose (e.g., "Panther Assessment") and leave expiration date blank 
7.	Click "Generate Token"
8.	Copy the generated token (it will only be shown once). 
9.	Paste the token into the Panther Assessment authentication window. The token is stored securely in Windows Credential Manager. Important: Your Canvas API token is stored securely on your computer and is only used to communicate with Canvas. Never share your token with others.
10.	Click "Connect"

A User Guide is included within the program for details on using the software.

## Troubleshooting

**Application won't open**: Make sure you've followed the "Run anyway" steps above.

**Canvas connection fails**: Verify your API token is correct and hasn't expired.
