document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('foundation-form');
    const progressBar = document.querySelector('.progress-bar');
    const requiredFields = form.querySelectorAll('[required]');
    
    // Update progress as fields are filled
    function updateProgress() {
        const totalRequired = requiredFields.length;
        const filledRequired = Array.from(requiredFields)
            .filter(field => field.value.trim() !== '').length;
        const progress = (filledRequired / totalRequired) * 100;
        
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }

    // Add validation styling on blur
    requiredFields.forEach(field => {
        field.addEventListener('blur', function() {
            if (!this.value.trim()) {
                this.classList.add('invalid');
                this.parentElement.querySelector('.error-message').style.display = 'block';
            } else {
                this.classList.remove('invalid');
                this.parentElement.querySelector('.error-message').style.display = 'none';
            }
        });

        field.addEventListener('input', updateProgress);
    });

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Check all required fields
        let isValid = true;
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('invalid');
                field.parentElement.querySelector('.error-message').style.display = 'block';
                isValid = false;
            }
        });

        if (!isValid) {
            return;
        }

        // Collect form data
        const formData = {
            foundation: {
                name: form.name.value,
                age: parseInt(form.age.value),
                pronoun: form.pronoun.value,
                location: form.location.value,
                relationship: form.relationship.value,
                children: form.children.value,
                pets: form.pets.value
            }
        };

        try {
            const response = await fetch('/api/v1/foundation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();
            console.log('API Response:', data);
            
            if (data.status === 'success') {
                // Store IDs in session storage for next steps
                sessionStorage.setItem('persona_id', data.data.persona_id);
                sessionStorage.setItem('test_run_id', data.data.test_run_id);
                
                // Redirect to core vision with IDs
                window.location.href = `/core-vision?persona_id=${data.data.persona_id}&test_run_id=${data.data.test_run_id}`;
            } else {
                throw new Error(data.error.message);
            }
        } catch (error) {
            alert('Error saving foundation: ' + error.message);
        }
    });
}); 