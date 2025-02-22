document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('actualization-form');
    const backButton = document.getElementById('back-to-core-vision');
    const submitButton = document.getElementById('submit-actualization');
    const persona_id = sessionStorage.getItem('persona_id');
    const test_run_id = sessionStorage.getItem('test_run_id');

    if (!persona_id || !test_run_id) {
        window.location.href = '/foundation';
        return;
    }

    // Load saved responses
    document.querySelectorAll('textarea').forEach(textarea => {
        const savedResponse = textarea.dataset.response;
        if (savedResponse) {
            textarea.value = savedResponse;
        }
    });

    // Track if responses have changed
    let responsesChanged = false;
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('input', () => {
            responsesChanged = true;
        });
    });

    // Also track variation changes
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', () => {
            responsesChanged = true;
        });
    });

    // Handle back button
    backButton.addEventListener('click', async function(e) {
        e.preventDefault();
        
        try {
            if (responsesChanged) {
                // Save responses first
                await saveResponses();
                
                // Run pipeline if responses changed
                await fetch('/api/v1/pipeline/run', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        test_run_id: test_run_id,
                        persona_id: persona_id
                    })
                });
            }
            
            window.location.href = `/core-vision?persona_id=${persona_id}&test_run_id=${test_run_id}`;
        } catch (error) {
            console.error('Error:', error);
            alert('Error saving responses: ' + error.message);
        }
    });

    // Handle form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        submitButton.disabled = true;
        
        try {
            await saveResponses();
            
            // Only run pipeline if responses changed
            if (responsesChanged) {
                // Clear existing story since inputs are changing
                await fetch(`/api/v1/story/clear/${test_run_id}`, {
                    method: 'POST'
                });
                
                await fetch('/api/v1/pipeline/run', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        test_run_id: test_run_id,
                        persona_id: persona_id
                    })
                });
            }

            window.location.href = `/stories?persona_id=${persona_id}&test_run_id=${test_run_id}`;
        } catch (error) {
            console.error('Error:', error);
            alert('There was an error processing your responses. Please try again.');
            submitButton.disabled = false;
        }
    });

    // Handle Next button click
    document.getElementById('next').addEventListener('click', function() {
        window.location.href = `/stories?persona_id=${persona_id}&test_run_id=${test_run_id}`;
    });

    async function saveResponses() {
        const responses = [];
        const sessionResponses = {};
        document.querySelectorAll('textarea').forEach(textarea => {
            if (textarea.value.trim()) {
                const promptId = textarea.dataset.promptId;
                const variationId = document.querySelector(`input[name="variation_${promptId}"]:checked`)?.value || 0;
                
                responses.push({
                    prompt_id: promptId,
                    variation_id: variationId,
                    response_text: textarea.value,
                    persona_id: persona_id,
                    test_run_id: test_run_id
                });
                // Save to session storage
                sessionResponses[promptId] = {
                    response_text: textarea.value,
                    variation_id: variationId
                };
            }
        });

        // Store in session
        sessionStorage.setItem('actualization_responses', JSON.stringify(sessionResponses));

        try {
            // Save responses to database
            for (const response of responses) {
                await fetch('/api/v1/responses', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        test_run_id: test_run_id,
                        persona_id: persona_id,
                        prompt_id: response.prompt_id,
                        variation_id: response.variation_id,
                        response_text: response.response_text
                    })
                });
            }
        } catch (error) {
            console.error('Error saving responses:', error);
            throw error;
        }
    }
});