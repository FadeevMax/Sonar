// DOM elements
const searchForm = document.getElementById('search-form');
const strainInput = document.getElementById('strain-input');
const chatContainer = document.getElementById('chat-container');
const chatMessages = document.getElementById('chat-messages');
const typingIndicator = document.getElementById('typing-indicator');
const suggestionsContainer = document.getElementById('suggestions-container');
const suggestionBtns = document.querySelectorAll('.suggestion-btn');
const loadingOverlay = document.getElementById('loading-overlay');

// Chat state
let isTyping = false;
let conversationHistory = [];

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Add event listeners
    searchForm.addEventListener('submit', handleSearch);
    
    // Add suggestion button listeners
    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const strain = this.getAttribute('data-strain');
            searchStrain(strain);
        });
    });
    
    // Focus on input
    strainInput.focus();
    
    // Add enter key listener for better UX
    strainInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSearch(e);
        }
    });
}

async function handleSearch(e) {
    e.preventDefault();
    
    const query = strainInput.value.trim();
    if (!query) return;
    
    await searchStrain(query);
    strainInput.value = '';
}

async function searchStrain(query) {
    if (isTyping) return;
    
    // Show chat container if hidden
    chatContainer.classList.add('active');
    
    // Hide suggestions after first search
    if (conversationHistory.length === 0) {
        suggestionsContainer.style.display = 'none';
    }
    
    // Add user message
    addMessage(query, 'user');
    
    // Show typing indicator
    showTyping();
    
    try {
        // Make API call to backend
        const response = await fetch('/api/strain-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                conversation_history: conversationHistory
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTyping();
        
        // Add bot response
        addMessage(data.response, 'bot');
        
        // Update conversation history
        conversationHistory.push({
            role: 'user',
            content: query
        });
        conversationHistory.push({
            role: 'assistant',
            content: data.response
        });
        
        // Keep conversation history manageable (last 10 exchanges)
        if (conversationHistory.length > 20) {
            conversationHistory = conversationHistory.slice(-20);
        }
        
    } catch (error) {
        console.error('Error searching strain:', error);
        hideTyping();
        
        // Show error message
        const errorMessage = `Sorry, I'm having trouble connecting to the strain database right now. Please try again in a moment. 

If you're looking for "${query}", I'd normally provide information about its effects, THC/CBD levels, genetics, and user reviews.`;
        
        addMessage(errorMessage, 'bot');
    }
}

function addMessage(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    const messageText = document.createElement('div');
    messageText.className = 'message-text';
    
    // Process message content for better formatting
    if (sender === 'bot') {
        messageText.innerHTML = formatBotMessage(content);
    } else {
        messageText.textContent = content;
    }
    
    messageContent.appendChild(messageText);
    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Animate message appearance
    messageDiv.style.opacity = '0';
    messageDiv.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
        messageDiv.style.transition = 'all 0.3s ease-out';
        messageDiv.style.opacity = '1';
        messageDiv.style.transform = 'translateY(0)';
    }, 50);
}

function formatBotMessage(content) {
    // Convert markdown-style formatting to HTML
    let formatted = content
        // Bold text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic text
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Line breaks
        .replace(/\n/g, '<br>')
        // Bullet points
        .replace(/^- (.*$)/gim, '• $1');
    
    return formatted;
}

function showTyping() {
    isTyping = true;
    typingIndicator.classList.add('active');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTyping() {
    isTyping = false;
    typingIndicator.classList.remove('active');
}

// Add some interactive features
function addQuickReplies(replies) {
    const quickRepliesDiv = document.createElement('div');
    quickRepliesDiv.className = 'quick-replies';
    
    replies.forEach(reply => {
        const button = document.createElement('button');
        button.className = 'quick-reply-btn';
        button.textContent = reply;
        button.addEventListener('click', () => {
            searchStrain(reply);
            quickRepliesDiv.remove();
        });
        quickRepliesDiv.appendChild(button);
    });
    
    chatMessages.appendChild(quickRepliesDiv);
}

// Handle network status
window.addEventListener('online', function() {
    console.log('Connection restored');
});

window.addEventListener('offline', function() {
    console.log('Connection lost');
    addMessage('⚠️ Connection lost. Please check your internet connection and try again.', 'bot');
});

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Focus input with Ctrl/Cmd + K
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        strainInput.focus();
        strainInput.select();
    }
    
    // Clear chat with Ctrl/Cmd + Shift + C
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'C') {
        e.preventDefault();
        clearChat();
    }
});

function clearChat() {
    // Keep welcome message but remove others
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    chatMessages.innerHTML = '';
    if (welcomeMessage) {
        chatMessages.appendChild(welcomeMessage);
    }
    
    // Reset conversation history
    conversationHistory = [];
    
    // Show suggestions again
    suggestionsContainer.style.display = 'block';
    
    // Hide chat container if no messages
    if (chatMessages.children.length <= 1) {
        chatContainer.classList.remove('active');
    }
}

// Add smooth scroll behavior for better UX
function smoothScrollToBottom() {
    chatMessages.scrollTo({
        top: chatMessages.scrollHeight,
        behavior: 'smooth'
    });
}

// Debounce function for search suggestions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Add search suggestions as user types (optional feature)
const debouncedSuggestions = debounce(function(query) {
    if (query.length > 2) {
        // Could add live search suggestions here
        console.log('Getting suggestions for:', query);
    }
}, 300);

strainInput.addEventListener('input', function() {
    debouncedSuggestions(this.value);
});