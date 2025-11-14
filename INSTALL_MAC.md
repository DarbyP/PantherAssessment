# Mac Installation Instructions

## Download

1. Go to the [latest release](../../releases/latest)
2. Download `PantherAssessment-Mac.zip`
3. Double-click to extract the application

## First Launch

macOS Gatekeeper will prevent the application from running initially because it's not code-signed.

1. **Do not double-click the application**
2. Right-click (or Control+click) on `PantherAssessment.app`
3. Select **"Open"** from the menu
4. Click **"Open"** in the security dialog

This process only needs to be done once. After this, you can launch normally.

### Alternative Method

If right-clicking doesn't work:
1. Open System Preferences → Security & Privacy
2. Try to open the application normally
3. In Security & Privacy, click "Open Anyway"

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

**"App is damaged" error**: macOS quarantines downloaded files. Run this in Terminal:
```bash
xattr -cr /path/to/PantherAssessment.app
```

**Canvas connection fails**: Verify your API token is correct and hasn't expired.
