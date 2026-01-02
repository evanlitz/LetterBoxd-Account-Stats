// Form handling and streaming progress
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('recommendForm');
    const submitBtn = document.getElementById('submitBtn');
    const loadingMessage = document.getElementById('loadingMessage');
    const progressContainer = document.getElementById('progressContainer');

    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent normal form submission

            // Get form data
            const formData = new FormData(form);

            // Show progress container
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';
            if (progressContainer) {
                progressContainer.style.display = 'block';
                resetProgress();
            } else {
                // Fallback to simple loading
                loadingMessage.style.display = 'block';
            }

            // Start streaming
            startStreaming(formData);
        });
    }

    function resetProgress() {
        // Reset all progress steps
        for (let i = 1; i <= 4; i++) {
            const step = document.querySelector(`.progress-step-live[data-step="${i}"]`);
            if (step) {
                step.classList.remove('active', 'completed');
            }
            const detail = document.getElementById(`step${i}-detail`);
            if (detail) {
                detail.textContent = 'Waiting...';
            }
            const progress = document.getElementById(`step${i}-progress`);
            if (progress) {
                progress.style.width = '0%';
            }
        }
    }

    function updateStep(stepNum, message, progress = 0, completed = false) {
        const step = document.querySelector(`.progress-step-live[data-step="${stepNum}"]`);
        const detail = document.getElementById(`step${stepNum}-detail`);
        const progressBar = document.getElementById(`step${stepNum}-progress`);

        if (step) {
            if (completed) {
                step.classList.remove('active');
                step.classList.add('completed');
            } else {
                step.classList.add('active');
            }
        }

        if (detail) {
            detail.textContent = message;
        }

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }

    function updateCurrentMessage(message) {
        const currentMessage = document.getElementById('currentMessage');
        if (currentMessage) {
            currentMessage.textContent = message;
        }
    }

    function startStreaming(formData) {
        // Create URL-encoded form data for POST
        const params = new URLSearchParams(formData);

        // Use fetch with streaming for POST
        fetch('/recommend-stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: params.toString()
        })
        .then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            function readStream() {
                return reader.read().then(({ done, value }) => {
                    if (done) {
                        console.log('Stream complete');
                        return;
                    }

                    // Decode the chunk
                    const chunk = decoder.decode(value, { stream: true });

                    // Process SSE messages
                    const lines = chunk.split('\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.substring(6));
                            handleProgressEvent(data);
                        }
                    }

                    // Continue reading
                    return readStream();
                });
            }

            return readStream();
        })
        .catch(error => {
            console.error('Streaming error:', error);
            updateCurrentMessage('Error: ' + error.message);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Get Recommendations';
        });
    }

    function handleProgressEvent(data) {
        console.log('Progress event:', data);

        if (data.type === 'progress') {
            const step = data.step;
            let progress = 0;

            // Calculate progress percentage
            if (data.current && data.total) {
                progress = (data.current / data.total) * 100;
            } else if (data.completed) {
                progress = 100;
            }

            updateStep(step, data.message, progress, data.completed);
            updateCurrentMessage(data.message);
        }
        else if (data.type === 'complete') {
            // Success! Redirect to results page
            updateCurrentMessage('✓ Complete! Displaying results...');

            // Store results in sessionStorage
            sessionStorage.setItem('recommendations', JSON.stringify(data.recommendations));
            sessionStorage.setItem('stats', JSON.stringify(data.stats));

            // Redirect to results page (we'll need to create a client-side results page)
            // For now, let's create a form and submit it to the regular endpoint
            displayResults(data.recommendations, data.stats);
        }
        else if (data.type === 'error') {
            // Show error
            updateCurrentMessage('Error: ' + data.message);
            const step = data.step || 0;
            if (step > 0) {
                updateStep(step, 'Error: ' + data.message, 0, false);
            }

            // Re-enable submit button
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Get Recommendations';
            }, 2000);
        }
    }

    function displayResults(recommendations, stats) {
        // Create a temporary form to submit results to results page
        const resultForm = document.createElement('form');
        resultForm.method = 'POST';
        resultForm.action = '/display-results';
        resultForm.style.display = 'none';

        // Add recommendations as JSON
        const recsInput = document.createElement('input');
        recsInput.type = 'hidden';
        recsInput.name = 'recommendations';
        recsInput.value = JSON.stringify(recommendations);
        resultForm.appendChild(recsInput);

        // Add stats as JSON
        const statsInput = document.createElement('input');
        statsInput.type = 'hidden';
        statsInput.name = 'stats';
        statsInput.value = JSON.stringify(stats);
        resultForm.appendChild(statsInput);

        document.body.appendChild(resultForm);
        resultForm.submit();
    }

    // URL validation
    const urlInput = document.getElementById('letterboxd_url');
    if (urlInput) {
        urlInput.addEventListener('input', function(e) {
            const url = e.target.value;

            // Check if it's a Letterboxd URL
            if (url && !url.includes('letterboxd.com') && !url.includes('boxd.it')) {
                urlInput.setCustomValidity('Please enter a valid Letterboxd URL');
            } else {
                urlInput.setCustomValidity('');
            }
        });
    }

    // Dark Mode Toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    const toggleIcon = darkModeToggle?.querySelector('.toggle-icon');

    // Check for saved user preference, default to light mode
    const currentTheme = localStorage.getItem('theme') || 'light';

    // Apply the theme on page load
    if (currentTheme === 'dark') {
        document.body.classList.add('dark-mode');
        if (toggleIcon) toggleIcon.textContent = 'LIGHT';
    } else {
        document.body.classList.remove('dark-mode');
        if (toggleIcon) toggleIcon.textContent = 'DARK';
    }

    // Toggle dark mode on button click
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');

            // Update icon based on current mode
            const isDarkMode = document.body.classList.contains('dark-mode');
            if (toggleIcon) {
                toggleIcon.textContent = isDarkMode ? 'LIGHT' : 'DARK';
            }

            // Save preference to localStorage
            localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
        });
    }
});
