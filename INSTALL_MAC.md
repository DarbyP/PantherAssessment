# Mac Installation Instructions

## Download

1. Go to the [latest release](../../releases/latest)
2. Download `PantherAssessment.dmg`
3. Double-click to open the package
4. Open your applications folder (or wherever you would like to keep the program) and drag Panther Assessment.app to that location. 

## First Launch

macOS Gatekeeper will ask if you are sure you want to open the program. Click **"Open"**

This process only needs to be done once. After this, you can launch normally.

## Canvas API Token

You'll need a Canvas API token to use the application:

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
9.	Paste the token into the Panther Assessment authentication window. The token is stored securely in macOS Keychain. Important: Your Canvas API token is stored securely on your computer and is only used to communicate with Canvas. Never share your token with others.
10.	Click "Connect"

A User Guide is included within the program for details on using the software.

## Troubleshooting

**Canvas connection fails**: Verify your API token is correct and hasn't expired.
