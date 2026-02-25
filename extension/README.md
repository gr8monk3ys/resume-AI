# ResuBoost AI Chrome Extension

Browser extension for ResuBoost AI that enables one-click job application autofill and job tracking directly from job boards.

## Features

- **Autofill Job Applications**: Automatically fill job application forms with your profile data
- **Platform Detection**: Supports LinkedIn, Greenhouse, Lever, Workday, Indeed, and more
- **Job Tracking**: Save jobs to your ResuBoost tracker with one click
- **Profile Sync**: Uses your ResuBoost profile data for consistent applications

## Supported Job Boards

| Platform | Status | Notes |
|----------|--------|-------|
| LinkedIn | Supported | Easy Apply and regular applications |
| Greenhouse | Supported | All Greenhouse-hosted job pages |
| Lever | Supported | All Lever-hosted job pages |
| Workday | Partial | Complex forms may require manual input |
| Indeed | Partial | Basic form filling |
| iCIMS | Planned | Detection only |
| SmartRecruiters | Planned | Detection only |
| Ashby | Planned | Detection only |
| BambooHR | Planned | Detection only |
| Breezy | Planned | Detection only |

## Installation

### Development Mode

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/resume-AI.git
   cd resume-AI/extension
   ```

2. Open Chrome and navigate to `chrome://extensions/`

3. Enable **Developer mode** (toggle in top right)

4. Click **Load unpacked** and select the `extension/` directory

5. The extension icon should appear in your browser toolbar

### Production Installation

> Coming soon to Chrome Web Store

## Development

### Project Structure

```
extension/
├── manifest.json          # Extension manifest (V3)
├── popup/                 # Popup UI
│   ├── popup.html
│   ├── popup.css
│   └── popup.js
├── content/               # Content scripts
│   ├── content.js         # Main content script
│   ├── detector.js        # Platform detection
│   └── fillers/           # Platform-specific fillers
│       ├── generic.js     # Base filler class
│       ├── linkedin.js
│       ├── greenhouse.js
│       ├── lever.js
│       └── workday.js
├── background/            # Background service worker
│   └── service-worker.js
├── lib/                   # Shared utilities
│   ├── api.js             # API client
│   └── storage.js         # Chrome storage helpers
├── icons/                 # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md
```

### Making Changes

1. Make your changes to the source files

2. Go to `chrome://extensions/`

3. Click the refresh icon on the ResuBoost AI extension card

4. Test your changes on a job board

### Debugging

- **Popup**: Right-click the extension icon and select "Inspect popup"
- **Content scripts**: Open DevTools on the job page, check Console for `[ResuBoost]` logs
- **Service worker**: Go to `chrome://extensions/`, click "Service worker" link on the extension card

### Adding Support for a New Platform

1. Add URL patterns to `manifest.json` under `host_permissions` and `content_scripts.matches`

2. Add platform detection to `content/detector.js`:
   ```javascript
   {
     name: 'newplatform',
     patterns: [/newplatform\.com/i],
     selectors: ['#application-form', '.apply-button'],
   }
   ```

3. Create a new filler in `content/fillers/newplatform.js`:
   ```javascript
   class NewPlatformFiller extends GenericFiller {
     constructor() {
       super()
       this.platform = 'newplatform'
     }

     async fill(profileData) {
       // Platform-specific filling logic
     }
   }
   ```

4. Add the filler to `manifest.json` content scripts

## Configuration

### API Configuration

The extension connects to the ResuBoost API at `http://localhost:8000` by default. To change this:

1. Edit `background/service-worker.js`:
   ```javascript
   const CONFIG = {
     API_BASE_URL: 'https://your-api-url.com/api',
     APP_URL: 'https://your-app-url.com',
   }
   ```

2. Edit `lib/api.js`:
   ```javascript
   const DEFAULT_API_URL = 'https://your-api-url.com/api'
   ```

3. Edit `popup/popup.js`:
   ```javascript
   const APP_URL = 'https://your-app-url.com'
   ```

### Permissions

The extension requests the following permissions:

- `activeTab`: Access the current tab to detect job pages
- `storage`: Store user preferences and cached data
- `tabs`: Query and interact with browser tabs

Host permissions are required for content script injection on supported job boards.

## Security

- Authentication tokens are stored in Chrome's local storage
- Tokens are automatically refreshed before expiration
- All API communication uses HTTPS (in production)
- No sensitive data is logged to console in production

## Troubleshooting

### Extension not detecting job page

1. Ensure you're on a supported job board URL
2. Wait for the page to fully load
3. Refresh the page and try again
4. Check if the job board uses a custom/embedded application form

### Autofill not working

1. Make sure you're logged in to ResuBoost
2. Check that your profile has the required fields filled
3. Some forms may require manual input for security fields
4. Check the console for error messages

### Connection issues

1. Verify the ResuBoost backend is running
2. Check CORS settings if using a custom API URL
3. Ensure your authentication token is valid

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-platform`
3. Make your changes
4. Test thoroughly on multiple job boards
5. Submit a pull request

## TODO

- [ ] Implement actual file upload for resumes
- [ ] Add support for more job boards
- [ ] Implement OAuth flow for login
- [ ] Add options page for settings
- [ ] Create production-ready icons
- [ ] Add automated testing
- [ ] Publish to Chrome Web Store

## License

MIT License - See LICENSE file for details
