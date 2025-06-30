class Chatbot {
    constructor() {
        this.chatHistory = [];
        this.userId = null;
        this.dbName = null;
        this.isLoading = false;
        this.init();
    }

    init() {
        // Get user ID and database name from localStorage
        const currentUser = JSON.parse(localStorage.getItem('currentUser'));
        this.userId = currentUser ? currentUser.user_id : null;
        
        // Get database name from URL parameters (same as workspace.js)
        const urlParams = new URLSearchParams(window.location.search);
        this.dbName = urlParams.get('db');
        
        console.log('Chatbot init - User ID:', this.userId, 'Database:', this.dbName);
        
        if (!this.userId || !this.dbName) {
            console.error('User ID or database name not found');
            console.error('User ID:', this.userId);
            console.error('Database:', this.dbName);
            return;
        }

        this.loadChatHistory();
        this.setupEventListeners();
    }

    setupEventListeners() {
        const sendButton = document.getElementById('chatbot-send-btn');
        const messageInput = document.getElementById('chatbot-message-input');
        const chatContainer = document.getElementById('chatbot-messages');

        if (sendButton) {
            sendButton.addEventListener('click', () => this.sendMessage());
        }

        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Auto-scroll to bottom when new messages are added
        if (chatContainer) {
            const observer = new MutationObserver(() => {
                this.scrollToBottom();
            });
            observer.observe(chatContainer, { childList: true, subtree: true });
        }
    }

    async loadChatHistory() {
        try {
            const response = await fetch(`http://127.0.0.1:5501/get-chat-history?user_id=${this.userId}&db_name=${this.dbName}`);
            const data = await response.json();
            
            if (data.chat_history) {
                this.chatHistory = data.chat_history;
                this.displayChatHistory();
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    displayChatHistory() {
        const chatContainer = document.getElementById('chatbot-messages');
        if (!chatContainer) return;

        chatContainer.innerHTML = '';
        
        this.chatHistory.forEach(chat => {
            if (chat.is_user_message) {
                this.addMessageToUI(chat.message, 'user');
            } else {
                this.addMessageToUI(chat.response, 'assistant');
            }
        });

        this.scrollToBottom();
    }

    async sendMessage() {
        const messageInput = document.getElementById('chatbot-message-input');
        const sendButton = document.getElementById('chatbot-send-btn');
        
        console.log('Send message called');
        console.log('Message input:', messageInput);
        console.log('Send button:', sendButton);
        
        if (!messageInput || !sendButton) {
            console.error('Message input or send button not found');
            return;
        }

        const message = messageInput.value.trim();
        console.log('Message to send:', message);
        
        if (!message || this.isLoading) {
            console.log('Message empty or already loading');
            return;
        }

        // Clear input and disable send button
        messageInput.value = '';
        this.isLoading = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        // Add user message to UI immediately
        this.addMessageToUI(message, 'user');

        try {
            console.log('Sending request to chatbot API...');
            const requestBody = {
                user_id: this.userId,
                db_name: this.dbName,
                message: message,
                chat_history: this.chatHistory
            };
            console.log('Request body:', requestBody);
            
            const response = await fetch('http://127.0.0.1:5501/send-message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            console.log('Response status:', response.status);
            const data = await response.json();
            console.log('Response data:', data);

            if (data.error) {
                this.addMessageToUI(`Error: ${data.error}`, 'assistant', 'error');
            } else {
                // Simply display the response without any execution functionality
                this.addMessageToUI(data.response, 'assistant');
                
                // Update chat history
                this.chatHistory.push({
                    message: message,
                    response: data.response,
                    timestamp: data.timestamp,
                    is_user_message: true
                });
                this.chatHistory.push({
                    message: '',
                    response: data.response,
                    timestamp: data.timestamp,
                    is_user_message: false
                });
            }
        } catch (error) {
            console.error('Error sending message:', error);
            let errorMessage = 'Sorry, I encountered an error. Please try again.';
            
            // Try to get more specific error information
            if (error.message) {
                errorMessage = `Error: ${error.message}`;
            }
            
            this.addMessageToUI(errorMessage, 'assistant', 'error');
        } finally {
            // Re-enable send button
            this.isLoading = false;
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    }

    addMessageToUI(message, sender, type = 'normal') {
        const chatContainer = document.getElementById('chatbot-messages');
        if (!chatContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chatbot-message ${sender}-message ${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${this.formatMessage(message)}</div>
                <div class="message-timestamp">${timestamp}</div>
            </div>
        `;

        chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(message) {
        // Convert line breaks to <br> tags
        message = message.replace(/\n/g, '<br>');
        
        // Format code blocks
        message = message.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang || 'sql'}">${code.trim()}</code></pre>`;
        });
        
        // Format inline code
        message = message.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        return message;
    }

    scrollToBottom() {
        const chatContainer = document.getElementById('chatbot-messages');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    clearChat() {
        const chatContainer = document.getElementById('chatbot-messages');
        if (chatContainer) {
            chatContainer.innerHTML = '';
        }
        this.chatHistory = [];
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new Chatbot();
}); 