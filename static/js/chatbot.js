$(document).ready(function() {
    const $chatMessages = $('#chat-messages');
    const $chatForm = $('#chat-form');
    const $questionInput = $('#question-input');
    const $loading = $('#loading');

    // Check if all required elements exist
    if (!$chatForm.length || !$questionInput.length || !$chatMessages.length || !$loading.length) {
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
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                const botResponse = `
                    <div class="answer-content">
                        ${data.answer}
                    </div>
                `;
                addMessage(botResponse);
            } else {
                addMessage('Sorry, I encountered an error: ' + response.message);
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Sorry, I encountered an error while processing your question. Please try again.');
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
});