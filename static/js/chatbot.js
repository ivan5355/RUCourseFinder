$(document).ready(function() {
    const $chatMessages = $('#chat-messages');
    const $chatForm = $('#chat-form');
    const $questionInput = $('#question-input');
    const $loading = $('#loading');

    // Check if all required elements exist
    if (!$chatForm.length || !$questionInput.length || !$chatMessages.length || !$loading.length) {
        console.error('Required elements not found');
        return;
    }

    // Store conversation history for context
    let conversationHistory = [];

    function addMessage(content, isUser = false) {
        const $messageDiv = $('<div>')
            .addClass(`message ${isUser ? 'user-message' : 'bot-message'}`)
            .html(content);
        
        $chatMessages.append($messageDiv);
        $chatMessages.scrollTop($chatMessages[0].scrollHeight);

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
        
        const question = $questionInput.val().trim();
        
        if (!question) {
            return;
        }

        // Add user message
        addMessage(question, true);
        $questionInput.val('');

        // Show loading
        $loading.show();
        
        try {
            const response = await $.ajax({
                url: '/ask_question',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    question: question,
                    conversation_history: conversationHistory.slice(0, -1)
                }),
                dataType: 'json'
            });
            
            // Response is already parsed JSON with $.ajax()
            if (response.status === 'success') {
                const botResponse = `
                    <div class="answer-content">
                        ${response.answer}
                    </div>
                `;
                addMessage(botResponse);
            } else {
                addMessage('Sorry, I encountered an error: ' + (response.message || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error:', error);
            
            // Handle different types of errors
            let errorMessage = 'Sorry, I encountered an error while processing your question. Please try again.';
            
            if (error.responseJSON && error.responseJSON.message) {
                errorMessage = 'Error: ' + error.responseJSON.message;
            } else if (error.statusText) {
                errorMessage = 'Network error: ' + error.statusText;
            }
            
            addMessage(errorMessage);
        } finally {
            $loading.hide();
        }
    }

    // Add form submit listener
    $chatForm.on('submit', handleSubmit);

    // Add Enter key listener to input
    $questionInput.on('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSubmit(event);
        }
    });

    console.log('Chatbot JavaScript loaded successfully');
});