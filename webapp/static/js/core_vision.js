document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('core-vision-form');
    const submitButton = document.getElementById('submit-core-vision');
    const persona_id = sessionStorage.getItem('persona_id');
    const test_run_id = sessionStorage.getItem('test_run_id');
    const MIN_CHARS = 50;

    console.log('Core Vision loaded with:', { persona_id, test_run_id });  // Debug log

    if (!persona_id || !test_run_id) {
        console.log('Missing IDs, redirecting to foundation');  // Debug log
        window.location.href = '/foundation';
        return;
    }

    // Add character counters to all textareas
    document.querySelectorAll('.response-area textarea').forEach(textarea => {
        const counter = document.createElement('div');
        counter.className = 'character-count';
        textarea.parentNode.appendChild(counter);
        
        // Add status indicator
        const status = document.createElement('div');
        status.className = 'prompt-status';
        const indicator = document.createElement('span');
        indicator.className = 'status-indicator';
        status.appendChild(indicator);
        textarea.parentNode.insertBefore(status, textarea);

        function updateCount() {
            const count = textarea.value.length;
            counter.textContent = `${count}/${MIN_CHARS} characters`;
            
            if (count < MIN_CHARS) {
                counter.classList.add('invalid');
                textarea.classList.add('invalid');
                indicator.classList.remove('complete');
            } else {
                counter.classList.remove('invalid');
                textarea.classList.remove('invalid');
                indicator.classList.add('complete');
            }
            
            checkFormValidity();
        }

        textarea.addEventListener('input', updateCount);
        updateCount();
    });

    function checkFormValidity() {
        const textareas = form.querySelectorAll('textarea');
        const allValid = Array.from(textareas).every(ta => ta.value.length >= MIN_CHARS);
        submitButton.disabled = !allValid;
    }

    async function saveResponses() {
        const responses = [];
        const sessionResponses = {};
        document.querySelectorAll('textarea').forEach(textarea => {
            const promptId = textarea.dataset.promptId;
            const responseText = textarea.value.trim();
            const variationId = document.querySelector(`input[name="prompt_${promptId}"]:checked`)?.value || 0;
            
            if (responseText) {
                responses.push({
                    prompt_id: promptId,
                    variation_id: variationId,
                    response_text: responseText,
                    persona_id: persona_id,
                    test_run_id: test_run_id
                });
                // Save to session storage
                sessionResponses[promptId] = {
                    response_text: responseText,
                    variation_id: variationId
                };
            }
        });

        // Store in session
        sessionStorage.setItem('core_vision_responses', JSON.stringify(sessionResponses));

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

    // Load saved responses from session storage
    const savedResponses = JSON.parse(sessionStorage.getItem('core_vision_responses') || '{}');
    document.querySelectorAll('.response-area textarea').forEach(textarea => {
        const promptId = textarea.dataset.promptId;
        const saved = savedResponses[promptId];
        
        if (saved) {
            textarea.value = saved.response_text;
            
            // Select the saved variation if one exists
            if (saved.variation_id) {
                const radio = document.querySelector(
                    `input[name="prompt_${promptId}"][value="${saved.variation_id}"]`
                );
                if (radio) {
                    radio.checked = true;
                }
            }
            
            // Update character count for saved response
            const event = new Event('input');
            textarea.dispatchEvent(event);
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

    // Handle form submission (Next button)
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        submitButton.disabled = true;
        
        try {
            // Save responses
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
            
            window.location.href = `/actualization?persona_id=${persona_id}&test_run_id=${test_run_id}`;
        } catch (error) {
            console.error('Error:', error);
            alert('Error saving responses: ' + error.message);
            submitButton.disabled = false;
        }
    });
}); 