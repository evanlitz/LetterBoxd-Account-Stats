// Profile analysis form handling and streaming progress
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('profileForm');
    const submitBtn = document.getElementById('submitBtn');
    const progressContainer = document.getElementById('progressContainer');

    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent normal form submission

            // Get form data
            const formData = new FormData(form);

            // Show progress container
            submitBtn.disabled = true;
            submitBtn.textContent = 'Analyzing...';
            if (progressContainer) {
                progressContainer.style.display = 'block';
                resetProgress();
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
        fetch('/analyze-profile-stream', {
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
            submitBtn.textContent = 'Analyze My Taste';
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
            // Success! Display results
            updateCurrentMessage('✓ Complete! Displaying your taste profile...');
            displayResults(data);
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
                submitBtn.textContent = 'Analyze My Taste';
            }, 2000);
        }
    }

    function displayResults(data) {
        // Create a temporary form to submit results to results page
        const resultForm = document.createElement('form');
        resultForm.method = 'POST';
        resultForm.action = '/display-profile-results';
        resultForm.style.display = 'none';

        // Package all data as JSON
        const resultsData = {
            username: data.username,
            analysis: data.analysis,
            recommendations: data.recommendations,
            enriched_movies: data.enriched_movies || []
        };

        const dataInput = document.createElement('input');
        dataInput.type = 'hidden';
        dataInput.name = 'results_data';
        dataInput.value = JSON.stringify(resultsData);
        resultForm.appendChild(dataInput);

        document.body.appendChild(resultForm);
        resultForm.submit();
    }

    // Username validation
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        usernameInput.addEventListener('input', function(e) {
            const username = e.target.value.trim();

            // Check if username is valid (alphanumeric, hyphens, underscores)
            if (username && !/^[a-zA-Z0-9_-]+$/.test(username)) {
                usernameInput.setCustomValidity('Username can only contain letters, numbers, hyphens, and underscores');
            } else {
                usernameInput.setCustomValidity('');
            }
        });
    }
});
