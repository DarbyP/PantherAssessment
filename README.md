# Panther Assessment

Panther Assessment is a powerful assessment reporting tool that helps faculty generate comprehensive outcome reports from the Canvas LMS. 

## Features

- Canvas LMS integration with secure API token authentication (one-time setup)
- Select specific courses and assignments
- Configure outcomes/assessment items using assignments, rubric sections or quiz question groups,including outcomes that span multiple assignments
- Save templates for reuse across semesters
- Generate Excel reports showing student performance on learning outcomes

## Installation

Download the latest release for your platform:
- [Windows Installer](../../releases/latest)
- [Mac Application](../../releases/latest)

**Note**: These applications are not code-signed. You will see security warnings when first opening them.

### Windows
After downloading, Windows SmartScreen will warn you. Click "More info" then "Run anyway".

### Mac
After downloading, right-click the application and select "Open" (don't double-click). Click "Open" in the security dialog.

For detailed instructions, see [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) or [INSTALL_MAC.md](INSTALL_MAC.md).

## Initial Setup and Authentication
When you first launch Panther Assessment, you will be prompted to authenticate with Canvas. Follow these steps:
1.	When you open the program, it will prompt you to enter your university’s Canvas url. Be sure you enter the direct URL (e.g., https://university.instructure.com) rather than a redirect URL (https://canvas.university.edu).
2.	After entering the Canvas URL, the Canvas authentication window will open 
3.	Click the "Open Canvas" button to visit Canvas in your browser
4.	In Canvas, go to Account → Settings → Approved Integrations
5.	Click "+ New Access Token"
6.	Enter a purpose (e.g., "Panther Assessment") and leave expiration date blank 
7.	Click "Generate Token"
8.	Copy the generated token (it will only be shown once)
9.	Paste the token into the Panther Assessment authentication window
10.	Click "Connect"

A User Guide is included within the program for details on using the software.

## Requirements

- Canvas LMS account with API access
- Internet connection for Canvas API calls

## Support

For issues or questions, please [open an issue](../../issues).

## License

[Your chosen license - MIT is common for academic tools]
