document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('registerForm');

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value.trim();
        const confirmPassword = document.getElementById('confirmPassword').value.trim();

        if (password !== confirmPassword) {
            alert('Passwords do not match.');
            return;
        }

        try {
            const response = await fetch('http://127.0.0.1:5501/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });

            const result = await response.json();

            if (response.status === 201) {
                alert("✅ Registered successfully. Redirecting...");
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 1500);
            } else {
                alert(result.error || "Registration failed.");
            }
        } catch (err) {
            alert('❌ Error connecting to backend.');
            console.error(err);
        }
    });
});
