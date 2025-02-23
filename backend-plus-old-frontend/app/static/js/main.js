console.log('Website Entity Scraper - Frontend Initialized');

// Only run URL validation setup on the index page
(function() {
    // Check if we're on the index page by looking for the analyze form
    const urlInput = document.getElementById('url');
    const analyzeForm = document.getElementById('analyzeForm');
    const errorMessage = document.getElementById('errorMessage');
    
    if (urlInput && analyzeForm) {
        document.addEventListener('DOMContentLoaded', function() {
            // Handle form submission
            analyzeForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const inputUrl = urlInput.value;
                console.log('Attempting to validate URL:', inputUrl);
                
                const result = urlValidator.validateAndNormalize(inputUrl);
                if (result.isValid) {
                    console.log('URL validation successful:', result.url);
                    window.location.href = `/loading?url=${encodeURIComponent(result.url)}`;
                } else {
                    console.error('URL validation failed:', {
                        input: inputUrl,
                        error: result.error,
                        cleanedUrl: result.url
                    });
                    
                    // Show error in the UI
                    errorMessage.textContent = result.error;
                    errorMessage.classList.remove('d-none');
                }
            });

            // Clear error message when user starts typing
            urlInput.addEventListener('input', function() {
                errorMessage.classList.add('d-none');
            });
        });
    }
})();
