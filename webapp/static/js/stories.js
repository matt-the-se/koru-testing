// Independent functions for story management
async function pollForStoryCompletion(test_run_id) {
    return new Promise((resolve, reject) => {
        const pollInterval = setInterval(async () => {
            try {
                const storyResponse = await fetch(`/api/v1/story/${test_run_id}`);
                const storyData = await storyResponse.json();
                console.log('Polling story data:', storyData);
                
                if (storyData.status === 'complete' && storyData.content) {
                    clearInterval(pollInterval);
                    resolve(storyData);
                } else if (storyData.status === 'error') {
                    clearInterval(pollInterval);
                    reject(new Error('Story generation failed'));
                }
            } catch (error) {
                clearInterval(pollInterval);
                reject(error);
            }
        }, 2000);

        // Safety timeout after 2 minutes
        setTimeout(() => {
            clearInterval(pollInterval);
            reject(new Error('Story generation timed out'));
        }, 120000);
    });
}

async function checkExistingStory(test_run_id) {
    const response = await fetch(`/api/v1/story/${test_run_id}`);
    return await response.json();
}

async function startStoryGeneration(test_run_id, persona_id) {
    const response = await fetch('/api/v1/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test_run_id, persona_id })
    });
    
    if (!response.ok) {
        throw new Error('Failed to start story generation');
    }
}

// Main document ready handler
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
    const listenButton = document.getElementById('listen-story');
    const storyText = document.querySelector('.story-text');
    
    const persona_id = sessionStorage.getItem('persona_id');
    const test_run_id = sessionStorage.getItem('test_run_id');

    if (!persona_id || !test_run_id) {
        window.location.href = '/foundation';
        return;
    }

    // Initial state check
    async function initializePage() {
        try {
            const storyData = await checkExistingStory(test_run_id);
            console.log('Initial story check:', storyData);

            if (storyData.status === 'complete' && storyData.content) {
                // Show existing story
                storyContent.querySelector('.story-text').textContent = storyData.content;
                storyContent.style.display = 'block';
                generateBtn.style.display = 'none';
                finishButton.disabled = false;
                finishButton.title = '';
            } else {
                // Check if we can generate new story
                const canGenerate = await fetch(`/api/v1/story/can-generate/${test_run_id}`);
                const generateData = await canGenerate.json();
                
                // Only show generate button if allowed
                generateBtn.style.display = generateData.can_generate ? 'block' : 'none';
                generateBtn.disabled = false;
                generateBtn.classList.remove('generating');
            }
        } catch (error) {
            console.error('Error checking story:', error);
            generateBtn.style.display = 'block';
            generateBtn.disabled = false;
        }
    }

    // Generate button handler
    generateBtn.addEventListener('click', async function() {
        try {
            generateBtn.disabled = true;
            generateBtn.classList.add('generating');
            generateBtn.innerHTML = 'Generating<br>Story...';
            
            await startStoryGeneration(test_run_id, persona_id);
            const storyData = await pollForStoryCompletion(test_run_id);
            
            // Show completed story
            storyContent.querySelector('.story-text').textContent = storyData.content;
            storyContent.style.display = 'block';
            generateBtn.style.display = 'none';
            finishButton.disabled = false;
            finishButton.title = '';
            
        } catch (error) {
            console.error('Error generating story:', error);
            alert(error.message || 'Error generating story. Please try again.');
            generateBtn.disabled = false;
            generateBtn.classList.remove('generating');
            generateBtn.innerHTML = 'Generate<br>Story';
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

    // Add audio playback handling
    let audio = null;
    let speaking = false;
    
    listenButton.addEventListener('click', async function() {
        if ('speechSynthesis' in window) {
            if (speaking) {
                window.speechSynthesis.cancel();
                speaking = false;
                listenButton.innerHTML = '<i class="fas fa-play"></i> Listen';
                return;
            }
            
            const text = storyText.textContent;
            const utterance = new SpeechSynthesisUtterance(text);
            
            utterance.onstart = () => {
                speaking = true;
                listenButton.innerHTML = '<i class="fas fa-pause"></i> Pause';
            };
            
            utterance.onend = () => {
                speaking = false;
                listenButton.innerHTML = '<i class="fas fa-play"></i> Listen';
            };
            
            window.speechSynthesis.speak(utterance);
        } else {
            alert('Text-to-speech is not supported in your browser');
        }
    });

    // Initialize page
    initializePage();
}); 