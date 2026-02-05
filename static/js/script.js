/**
 * PWD Assistant - Final Consolidated JavaScript File
 *
 * This file contains all the JavaScript functionality for the entire website,
 * including the Services Hub search, the Video Guide search, and the Chatbot.
 */

// --- Function for Services Hub (planner.html) ---
// This function is called by the 'onclick' attribute on the search button in planner.html.
function searchResources() {
    const domain = document.getElementById("domain").value;
    const location = document.getElementById("location").value.trim();
    const resultDiv = document.getElementById("planResult");

    if (!domain || !location) {
        if(resultDiv) {
            resultDiv.innerHTML = `<div class="card" style="text-align: center; color: #c62828; background-color: #ffebee; padding: 20px;"><strong>Please complete all fields to perform a search.</strong></div>`;
            resultDiv.style.display = 'block';
        }
        return;
    }

    // This is a placeholder for your mock data logic.
    let headerText = `Displaying mock results for ${domain} in ${location}`;
    if(resultDiv) {
        resultDiv.innerHTML = `<div class="result-header"><h2>${headerText}</h2></div>`;
        resultDiv.style.display = 'block';
        resultDiv.scrollIntoView({ behavior: 'smooth' });
    }
}

// --- Function for Video Guide (guide.html) ---
// This function is called by the 'onclick' attribute on the search button in guide.html.
function searchVideos(query) {
    const searchInput = document.getElementById('searchInput');
    const videoContainer = document.getElementById('videoContainer');
    const searchTerm = query || (searchInput ? searchInput.value.trim() : '');

    if (!searchTerm) {
        alert('Please enter a search topic.');
        return;
    }

    if(videoContainer) {
        videoContainer.innerHTML = `<p style="text-align:center; padding: 20px;">Showing mock video results for "${searchTerm}"...</p>`;
    }
}


// --- Main Event Listener for Page Load ---
// This runs after the entire HTML document is loaded, setting up the chatbot.
document.addEventListener('DOMContentLoaded', () => {

    // --- Chatbot Logic (Runs on all pages) ---
    const openChatbotBtn = document.getElementById('open-chatbot-btn');
    const chatbotContainer = document.getElementById('chatbot-container');
    const closeChatbotBtn = document.getElementById('close-chatbot-btn');
    const chatForm = document.getElementById('chat-form');
    const chatInputField = document.getElementById('chat-input-field');
    const chatBody = document.getElementById('chat-body');

    // This check prevents errors if the chatbot HTML isn't on a page.
    if (openChatbotBtn && chatbotContainer && closeChatbotBtn && chatForm) {

        openChatbotBtn.addEventListener('click', () => {
            chatbotContainer.style.display = 'flex';
        });

        closeChatbotBtn.addEventListener('click', () => {
            chatbotContainer.style.display = 'none';
        });

        chatForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const userMessage = chatInputField.value.trim();
            if (userMessage) {
                addMessageToChat('user', userMessage);
                chatInputField.value = '';
                setTimeout(() => {
                    const botResponse = generateBotResponse(userMessage);
                    addMessageToChat('bot', botResponse);
                }, 1000);
            }
        });
    }

    function addMessageToChat(sender, message) {
        if (!chatBody) return; // Safety check
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `chat-message ${sender}-message`;
        messageWrapper.innerHTML = `<p>${message}</p>`;
        chatBody.appendChild(messageWrapper);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function generateBotResponse(userInput) {
        const input = userInput.toLowerCase();
        if (input.includes('hello') || input.includes('hi')) return 'Hello there! How can I assist you today?';
        if (input.includes('scheme') || input.includes('pension')) return 'You can find detailed information on government schemes in our "Services Hub".';
        if (input.includes('help') || input.includes('support')) return 'I am here to help. You can ask me about services, resources, or the community forum.';
        if (input.includes('thank')) return 'You\'re welcome! Is there anything else I can help with?';
        return "I'm sorry, I'm still learning. Try asking about 'schemes' or 'help'.";
    }
});