// URL Validation Utility
class URLValidator {
    /**
     * Validates and normalizes a URL
     * @param {string} url - The URL to validate
     * @returns {object} - Object containing validation result and normalized URL
     */
    validateAndNormalize(url) {
        if (!url) return {
            isValid: false,
            url: '',
            error: 'Please enter a URL'
        };

        // Remove leading/trailing whitespace and convert to lowercase
        let cleanUrl = url.trim().toLowerCase();

        // First try to parse as-is
        try {
            const urlObject = new URL(cleanUrl);
            return {
                isValid: true,
                url: urlObject.href,
                error: null
            };
        } catch (error) {
            // If parsing fails, try adding https://
            if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
                cleanUrl = 'https://' + cleanUrl;
            }
        }

        // Try parsing with added protocol
        try {
            const urlObject = new URL(cleanUrl);
            
            // Basic validation that hostname has at least one dot
            if (!urlObject.hostname.includes('.')) {
                return {
                    isValid: false,
                    url: cleanUrl,
                    error: 'Please enter a valid domain (e.g., example.com)'
                };
            }

            return {
                isValid: true,
                url: urlObject.href,
                error: null
            };
        } catch (error) {
            return {
                isValid: false,
                url: cleanUrl,
                error: 'Please enter a valid URL (e.g., example.com or https://example.com)'
            };
        }
    }
}

// Create global instance
const urlValidator = new URLValidator();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = URLValidator;
} 