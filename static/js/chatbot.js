// Simple chatbot script - direct approach

// Wait for page to load
window.addEventListener('load', function() {
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const questionInput = document.getElementById('question-input');
    const loading = document.getElementById('loading');

    if (!chatForm || !questionInput || !chatMessages || !loading) {
        return;
    }

    // Store conversation history for context
    let conversationHistory = [];

    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.innerHTML = content;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Add to conversation history
        conversationHistory.push({
            role: isUser ? 'user' : 'assistant',
            content: isUser ? content : content.replace(/<[^>]*>/g, ''),
            timestamp: new Date().toISOString()
        });

        // Keep only last 20 messages
        if (conversationHistory.length > 20) {
            conversationHistory = conversationHistory.slice(-20);
        }
    }

    async function handleSubmit(event) {
        event.preventDefault();
        
        const question = questionInput.value.trim();
        
        if (!question) {
            return;
        }

        // Add user message
        addMessage(question, true);
        questionInput.value = '';

        // Show loading
        loading.style.display = 'block';
        
        try {
            const response = await fetch('/ask_question', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: question,
                    conversation_history: conversationHistory.slice(0, -1)
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                const botResponse = `
                    <div class="answer-content">
                        ${data.answer}
                        ${data.relevant_courses ? `
                            <div class="relevant-courses">
                                <h4>Relevant Courses:</h4>
                                <ul>
                                    ${data.relevant_courses.map(course => `<li>${course}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                `;
                addMessage(botResponse);
            } else {
                addMessage(`Sorry, I encountered an error: ${data.message}`);
            }
        } catch (error) {
            addMessage('Sorry, I encountered an error while processing your question. Please try again.');
        } finally {
            loading.style.display = 'none';
        }
    }

    // Add form submit listener
    chatForm.addEventListener('submit', handleSubmit);

    // Add Enter key listener to input
    questionInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSubmit(event);
        }
    });
});