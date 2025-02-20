document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-story');
    const storyContent = document.getElementById('story-content');
    const backButton = document.getElementById('back-to-actualization');
    const startOverButton = document.getElementById('start-over');
    const finishButton = document.getElementById('finish');
    const modal = document.getElementById('confirm-modal');
    const confirmYes = document.getElementById('confirm-yes');
    const confirmNo = document.getElementById('confirm-no');
    const feedbackInput = document.getElementById('feedback');
    const submitFeedback = document.getElementById('submit-feedback');
    
    const persona_id = sessionStorage.getItem('persona_id');
    const test_run_id = sessionStorage.getItem('test_run_id');

    if (!persona_id || !test_run_id) {
        window.location.href = '/foundation';
        return;
    }

    generateBtn.addEventListener('click', async function() {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
        
        try {
            // Start generation
            const response = await fetch('/api/v1/stories', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    test_run_id: test_run_id,
                    persona_id: persona_id
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to start story generation');
            }
            
            // Poll for story completion
            const pollInterval = setInterval(async () => {
                const storyResponse = await fetch(`/api/v1/story/${test_run_id}`);
                const storyData = await storyResponse.json();
                
                if (storyData.status === 'complete') {
                    clearInterval(pollInterval);
                    generateBtn.style.display = 'none';
                    storyContent.textContent = storyData.content;
                    storyContent.style.display = 'block';
                    finishButton.disabled = false;
                    finishButton.title = '';
                } else if (storyData.status === 'error') {
                    clearInterval(pollInterval);
                    throw new Error('Story generation failed');
                }
            }, 2000); // Poll every 2 seconds
            
            // Stop polling after 2 minutes as a safety measure
            setTimeout(() => {
                clearInterval(pollInterval);
                if (generateBtn.disabled) {
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate Story';
                    alert('Story generation timed out. Please try again.');
                }
            }, 120000);
            
        } catch (error) {
            console.error('Error:', error);
            alert('Error generating story. Please try again.');
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Story';
        }
    });

    backButton.addEventListener('click', function() {
        window.location.href = `/actualization?persona_id=${persona_id}&test_run_id=${test_run_id}`;
    });

    startOverButton.addEventListener('click', function() {
        modal.style.display = 'block';
    });

    confirmYes.addEventListener('click', function() {
        sessionStorage.clear();
        window.location.href = '/foundation';
    });

    confirmNo.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    submitFeedback.addEventListener('click', async function() {
        const feedbackText = feedbackInput.value.trim();
        if (!feedbackText) return;
        
        try {
            await fetch('/api/v1/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    test_run_id: test_run_id,
                    persona_id: persona_id,
                    feedback: feedbackText
                })
            });
            
            feedbackInput.value = '';
            alert('Thank you for your feedback!');
            
        } catch (error) {
            console.error('Error:', error);
            alert('Error submitting feedback. Please try again.');
        }
    });
}); 