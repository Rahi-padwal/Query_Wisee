document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('http://127.0.0.1:5501/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const result = await response.json();

            if (response.status === 200) {
                // Store user in localStorage (using the user object from response)
                localStorage.setItem('user', JSON.stringify(result.user));
                localStorage.setItem('currentUser', JSON.stringify(result.user)); // Keep both for compatibility
                // Redirect to dashboard
                window.location.href = 'dashboard.html';
            } else {
                alert(result.error || "Login failed.");
            }
        } catch (err) {
            alert('❌ Error connecting to backend. Please check if the server is running.');
            console.error('Login error:', err);
        }
    });
});
