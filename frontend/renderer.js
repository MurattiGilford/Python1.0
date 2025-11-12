(() => {
  'use strict';

  const BACKEND = 'http://127.0.0.1:7861';

  // DOM elements
  const messagesEl = document.getElementById('messages');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const attachBtn = document.getElementById('attachBtn');
  const fileInput = document.getElementById('fileInput');
  const statusText = document.getElementById('statusText');
  const costValue = document.getElementById('costValue');
  const modelHint = document.getElementById('modelHint');
  const providerSelect = document.getElementById('provider-select');
  const chatHistoryList = document.getElementById('chatHistoryList');
  const chatHistorySidebar = document.getElementById('chatHistorySidebar');
  const chatHistoryToggle = document.getElementById('chatHistoryToggle');

  let totalCost = 0;
  let isProcessing = false;
  // FIXED: Use proper session ID
  let currentSessionId = `session_${Date.now()}`;
  let chatSessions = [];
  let availableProviders = {};
  let chatHistoryVisible = true;

  // Performance optimizations
  const messageCache = new Map();
  const requestQueue = [];
  let isProcessingQueue = false;
  const maxMessagesInDOM = 50;

  // ===== UTILITY FUNCTIONS =====

  function sanitize(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatCost(cents) {
    return `$${(cents / 100).toFixed(4)}`;
  }

  function autoResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
  }

  // ===== MARKDOWN & FORMATTING =====

  function formatMarkdown(text) {
    let formatted = text;

    // Code blocks with syntax highlighting
    formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      const language = lang || 'text';
      return `<pre><code class="language-${language}">${sanitize(code.trim())}</code></pre>`;
    });

    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Lists (unordered)
    formatted = formatted.replace(/^- (.+)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Headers
    formatted = formatted.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    formatted = formatted.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Links
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // URLs
    formatted = formatted.replace(
      /(?<![="'])(https?:\/\/[^\s<]+)/g,
      '<a href="$1" target="_blank">$1</a>'
    );

    // Newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
  }

  // ===== MESSAGE RENDERING =====

  function createMessageElement(messageObj) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${messageObj.role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Avatar
    const avatar = document.createElement('div');
    avatar.className = `avatar ${messageObj.role}-avatar`;
    if (messageObj.role === 'user') {
      avatar.textContent = 'You';
    } else {
      avatar.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="8" fill="url(#avatarGradient)"/>
        </svg>
      `;
    }

    // Bubble
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    // Format content with markdown and media
    const formattedContent = formatMessage(messageObj.content, messageObj.metadata?.media_url);
    bubble.innerHTML = formattedContent;

    // Metadata
    if (messageObj.metadata?.model || messageObj.metadata?.time || messageObj.metadata?.cost !== undefined) {
      const meta = document.createElement('div');
      meta.className = 'message-meta';

      const parts = [];
      if (messageObj.metadata.model) {
        const modelNames = {
          'zai-glm-4.5-flash': 'GLM-4.5-Flash',
          'zai-glm-4.6': 'GLM-4.6',
          'zai-glm-4.5v': 'GLM-4.5V',
          'kimi-k2-0905-preview': 'Kimi K2 0905',
          'kimi-k2-turbo-preview': 'Kimi K2 Turbo',
          'zai-cogview-4': 'CogView-4',
          'zai-cogvideox-3': 'CogVideoX-3',
          'fact_guard': 'Fact Check'
        };
        parts.push(modelNames[messageObj.metadata.model] || messageObj.metadata.model);
      }
      if (messageObj.metadata.time) parts.push(`${messageObj.metadata.time}ms`);
      if (messageObj.metadata.cost !== undefined) parts.push(formatCost(messageObj.metadata.cost));
      if (messageObj.metadata.strategy) {
        const strategyNames = {
          'free_tier': 'Free',
          'orchestrator_fallback': 'Orchestrator',
          'paid_precision': 'Precision',
          'image_generation': 'Image',
          'video_generation': 'Video',
          'manual_selection': 'Manual',
          'fallback_to_free': 'Fallback'
        };
        parts.push(strategyNames[messageObj.metadata.strategy] || messageObj.metadata.strategy);
      }

      meta.textContent = parts.join(' • ');
      bubble.appendChild(meta);
    }

    contentDiv.appendChild(avatar);
    contentDiv.appendChild(bubble);
    messageDiv.appendChild(contentDiv);

    // Apply syntax highlighting to code blocks
    if (window.Prism) {
      Prism.highlightAllUnder(messageDiv);
    }

    return messageDiv;
  }

  function addMessage(role, content, metadata = {}) {
    // Remove welcome section if it exists
    const welcomeSection = messagesEl.querySelector('.welcome-section');
    if (welcomeSection) {
      welcomeSection.remove();
    }

    // Create message object
    const messageObj = { role, content, metadata, id: Date.now() };

    // Add to cache
    messageCache.set(messageObj.id, messageObj);

    // Limit cache size
    if (messageCache.size > maxMessagesInDOM) {
      const firstKey = messageCache.keys().next().value;
      messageCache.delete(firstKey);

      // Remove from DOM
      const firstMessage = messagesEl.querySelector('.message');
      if (firstMessage) {
        firstMessage.remove();
      }
    }

    // Create and add message element
    const messageDiv = createMessageElement(messageObj);
    messagesEl.appendChild(messageDiv);

    scrollToBottom();
  }

  function formatMessage(text, mediaUrl) {
    // FIXED: NO media display in reading panel - just provide download link
    if (mediaUrl && (text.includes('Image Generated') || text.includes('🎨'))) {
      // Remove any image markdown
      text = text.replace(/!\[Generated Image\]\([^)]+\)/g, '');
      // Add download link instead of showing image
      text += `\n\n<a href="${mediaUrl}" target="_blank" class="media-download-link">🔗 Download Generated Image</a>`;
    }

    if (mediaUrl && (text.includes('Video Generated') || text.includes('🎬'))) {
      // Add download link instead of showing video
      text += `\n\n<a href="${mediaUrl}" target="_blank" class="media-download-link">🔗 Download Generated Video</a>`;
    }

    // Apply markdown formatting
    return formatMarkdown(text);
  }

  function showLoading(message = 'Thinking...') {
    const template = document.getElementById('loadingTemplate');
    const loadingEl = template.content.cloneNode(true);
    const bubble = loadingEl.querySelector('.message-bubble');

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';

    const text = document.createElement('div');
    text.style.fontStyle = 'italic';
    text.style.marginTop = '8px';
    text.textContent = message;

    bubble.innerHTML = '';
    bubble.appendChild(indicator);
    bubble.appendChild(text);

    messagesEl.appendChild(loadingEl);
    scrollToBottom();
  }

  function hideLoading() {
    const loadingMsg = messagesEl.querySelector('.loading-msg');
    if (loadingMsg) {
      loadingMsg.remove();
    }
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ===== CHAT HISTORY MANAGEMENT - FIXED FOR NEW API =====

  function toggleChatHistory() {
    chatHistoryVisible = !chatHistoryVisible;
    chatHistorySidebar.classList.toggle('collapsed');
  }

  // FIXED: Use new /chats/sessions endpoint
  async function loadChatSessions() {
    try {
      const response = await fetch(`${BACKEND}/chats/sessions`);
      const data = await response.json();

      if (data.ok && data.sessions) {
        chatSessions = data.sessions;
        renderChatSessionsList();
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    }
  }

  function renderChatSessionsList() {
    if (!chatHistoryList) return;

    chatHistoryList.innerHTML = '';

    chatSessions.forEach((session) => {
      const item = document.createElement('div');
      item.className = 'chat-history-item';

      const date = new Date(session.last_message_ts * 1000);
      const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

      item.innerHTML = `
        <div class="chat-item-content">
          <div class="chat-title">${sanitize(session.preview)}</div>
          <div class="chat-date">${dateStr} • ${session.message_count} msgs</div>
        </div>
        <button class="delete-chat-btn" onclick="window.deleteChat('${session.session_id}')" title="Delete chat">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 1 1 0V6z"/>
            <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1 1v1H4.5a1 1 0 0 1-1 1v1.438l.438.438A.5.5 0 0 1 5 6.5v7a.5.5 0 0 1 .5.5h5a.5.5 0 0 1 .5-.5v-7A.5.5 0 0 1 .062-.25l.438-.438V3.5z"/>
          </svg>
        </button>
      `;

      item.onclick = (e) => {
        if (!e.target.closest('.delete-chat-btn')) {
          loadChatSession(session.session_id);
        }
      };

      chatHistoryList.appendChild(item);
    });
  }

  // FIXED: Load session by session_id
  async function loadChatSession(sessionId) {
    try {
      const response = await fetch(`${BACKEND}/chats/history?session_id=${sessionId}`);
      const messages = await response.json();

      // Clear current messages
      messagesEl.innerHTML = '';

      // Set current session
      currentSessionId = sessionId;

      // Load session messages
      messages.forEach(msg => {
        addMessage(msg.role, msg.content, {});
      });
    } catch (error) {
      console.error('Failed to load chat session:', error);
    }
  }

  // ===== FILE GENERATION =====
  window.generateFile = (fileType) => {
    const modal = document.getElementById('fileGenModal');
    const typeSelect = document.getElementById('fileGenType');
    typeSelect.value = fileType;
    modal.style.display = 'block';

    // Pre-fill with current chat content if available
    const messages = document.querySelectorAll('.message.assistant .message-bubble');
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const content = lastMessage.textContent || lastMessage.innerText;
      document.getElementById('fileGenContent').value = content;
    }
  };

  window.closeFileGenModal = () => {
    document.getElementById('fileGenModal').style.display = 'none';
  };

  window.confirmFileGeneration = async () => {
    const content = document.getElementById('fileGenContent').value;
    const fileType = document.getElementById('fileGenType').value;
    const filename = document.getElementById('fileGenName').value || `generated_${Date.now()}.${fileType}`;

    if (!content.trim()) {
      alert('Please enter content for the file');
      return;
    }

    try {
      statusText.textContent = 'Generating file...';

      const response = await fetch(`${BACKEND}/generate/file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: content,
          type: fileType,
          filename: filename
        })
      });

      const data = await response.json();

      if (data.ok) {
        // Download the file
        window.open(`${BACKEND}${data.download_url}`, '_blank');
        statusText.textContent = 'File generated';

        // Add success message to chat
        addMessage('assistant', `✅ Generated ${fileType.toUpperCase()} file: ${data.filename}`, {
          model: 'file_generator',
          strategy: 'file_generation'
        });

        window.closeFileGenModal();
      } else {
        const errorMsg = data.error || 'File generation failed';
        alert(`Failed to generate file: ${errorMsg}`);
        statusText.textContent = 'Error';
      }
    } catch (error) {
      console.error('File generation error:', error);
      alert('Failed to generate file: ' + error.message);
      statusText.textContent = 'Error';
    }
  };

  // ===== DELETE CHAT FUNCTION - FIXED =====
  window.deleteChat = async (sessionId) => {
    if (!confirm('Are you sure you want to delete this chat session?')) return;

    try {
      const response = await fetch(`${BACKEND}/chats/delete/${sessionId}`, {
        method: 'DELETE'
      });

      const data = await response.json();

      if (data.ok) {
        // Reload chat sessions
        await loadChatSessions();

        // If deleted session was the current one, start new session
        if (sessionId === currentSessionId) {
          messagesEl.innerHTML = `
            <div class="welcome-section">
              <div class="welcome-icon">⚡</div>
              <h2 class="welcome-title">Nuclear-Powered AI Laboratory</h2>
              <p class="welcome-subtitle">Unlimited capabilities - No boundaries</p>
              <div class="capabilities">
                <div class="capability">
                  <span class="capability-icon">🧠</span>
                  <span>Manual Selection</span>
                </div>
                <div class="capability">
                  <span class="capability-icon">🎨</span>
                  <span>Image Gen</span>
                </div>
                <div class="capability">
                  <span class="capability-icon">🎬</span>
                  <span>Video Gen</span>
                </div>
                <div class="capability">
                  <span class="capability-icon">📄</span>
                  <span>All Files</span>
                </div>
                <div class="capability">
                  <span class="capability-icon">💰</span>
                  <span>Cost Tracking</span>
                </div>
                <div class="capability">
                  <span class="capability-icon">🔬</span>
                  <span>Research</span>
                </div>
              </div>
            </div>
          `;
          currentSessionId = `session_${Date.now()}`;
        }
      } else {
        throw new Error(data.error || 'Delete failed');
      }
    } catch (error) {
      alert('Failed to delete chat: ' + error.message);
    }
  };

  // ===== PROVIDER MANAGEMENT =====

  async function fetchProviders() {
    try {
      const response = await fetch(`${BACKEND}/providers`);
      const providers = await response.json();
      availableProviders = providers;

      // Update provider select dropdown
      providerSelect.innerHTML = '<option value="">Auto (Free Tier)</option>';

      for (const [key, provider] of Object.entries(providers)) {
        const option = document.createElement('option');
        option.value = key;

        const costText = provider.cost_per_1k > 0
          ? `$${provider.cost_per_1k}/1K tokens`
          : 'FREE';

        option.textContent = `${provider.model} (${provider.type}) - ${costText}`;
        providerSelect.appendChild(option);
      }

    } catch (error) {
      console.error('Error fetching providers:', error);
    }
  }

  function updateProviderHint() {
    const selectedProvider = providerSelect.value;
    if (selectedProvider && availableProviders[selectedProvider]) {
      const provider = availableProviders[selectedProvider];
      modelHint.textContent = `Selected: ${provider.model} (${provider.type})`;
    } else {
      modelHint.textContent = 'Auto (Free Tier)';
    }
  }

  // ===== CHAT FUNCTIONS - FIXED WITH SESSION SUPPORT =====

  async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isProcessing) return;

    requestQueue.push(text);

    if (!isProcessingQueue) {
      processQueue();
    }
  }

  async function processQueue() {
    if (requestQueue.length === 0) {
      isProcessingQueue = false;
      return;
    }

    isProcessingQueue = true;
    const text = requestQueue.shift();

    isProcessing = true;
    sendBtn.disabled = true;

    addMessage('user', text);
    messageInput.value = '';
    autoResize();

    // Detect type for loading message
    const textLower = text.toLowerCase();
    let loadingMsg = 'Thinking...';

    if (textLower.includes('image') || textLower.includes('draw') || textLower.includes('picture')) {
      loadingMsg = 'Generating image...';
    } else if (textLower.includes('video') || textLower.includes('animate')) {
      loadingMsg = 'Generating video...';
    }

    showLoading(loadingMsg);
    statusText.textContent = 'Processing...';

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const selectedProvider = providerSelect.value;

      // FIXED: Include session_id in request
      const response = await fetch(`${BACKEND}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: text,
          temperature: 0.4,
          max_tokens: 2048,
          provider: selectedProvider || null,
          session_id: currentSessionId  // FIXED: Send session ID
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      hideLoading();

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();

      // FIXED: Update currentSessionId from response
      if (data.session_id) {
        currentSessionId = data.session_id;
      }

      addMessage('assistant', data.result, {
        model: data.model_used,
        time: data.processing_time_ms,
        cost: data.cost_cents,
        strategy: data.strategy,
        media_url: data.media_url
      });

      totalCost += data.cost_cents;
      costValue.textContent = formatCost(totalCost);

      statusText.textContent = 'Online';

      if (data.model_used && availableProviders[data.model_used]) {
        const provider = availableProviders[data.model_used];
        modelHint.textContent = `Used: ${provider.model} (${data.strategy})`;
      }

      // Reload sessions after new message
      await loadChatSessions();

      setTimeout(() => processQueue(), 100);

    } catch (error) {
      hideLoading();
      if (error.name === 'AbortError') {
        addMessage('assistant', '⏱️ Request timed out. Please try again.', {});
      } else {
        addMessage('assistant', `❌ Error: ${error.message}`, {});
      }
      statusText.textContent = 'Error';
    } finally {
      isProcessing = false;
      sendBtn.disabled = false;
      messageInput.focus();
    }
  }

  // ===== FILE UPLOAD - FIXED =====

  async function handleFileUpload(file) {
    if (!file) return;

    statusText.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${BACKEND}/files/upload`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.ok) {
        // FIXED: Backend now returns minimal info, no instruction field
        // Send a request to analyze the file
        const selectedProvider = providerSelect.value;

        isProcessing = true;
        sendBtn.disabled = true;

        showLoading('Analyzing file...');
        statusText.textContent = 'Processing...';

        const chatResponse = await fetch(`${BACKEND}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task: `Analyze the file I just uploaded: ${file.name}`,
            temperature: 0.4,
            max_tokens: 2048,
            provider: selectedProvider || null,
            session_id: currentSessionId  // FIXED: Use current session
          })
        });

        hideLoading();

        if (!chatResponse.ok) {
          const error = await chatResponse.json();
          throw new Error(error.detail || `HTTP ${chatResponse.status}`);
        }

        const chatData = await chatResponse.json();

        // FIXED: Update session ID
        if (chatData.session_id) {
          currentSessionId = chatData.session_id;
        }

        addMessage('assistant', chatData.result, {
          model: chatData.model_used,
          time: chatData.processing_time_ms,
          cost: chatData.cost_cents,
          strategy: chatData.strategy,
          media_url: chatData.media_url
        });

        totalCost += chatData.cost_cents;
        costValue.textContent = formatCost(totalCost);

        statusText.textContent = 'Online';

        if (chatData.model_used && availableProviders[chatData.model_used]) {
          const provider = availableProviders[chatData.model_used];
          modelHint.textContent = `Used: ${provider.model} (${chatData.strategy})`;
        }

        // Reload chat sessions
        await loadChatSessions();

        isProcessing = false;
        sendBtn.disabled = false;
        messageInput.focus();

      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      hideLoading();
      statusText.textContent = 'Upload failed';
      alert(`Failed to upload file: ${error.message}`);
      isProcessing = false;
      sendBtn.disabled = false;
    }
  }

  // ===== EVENT LISTENERS =====

  sendBtn.addEventListener('click', sendMessage);

  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  messageInput.addEventListener('input', autoResize);

  attachBtn.addEventListener('click', () => {
    fileInput.click();
  });

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileUpload(file);
    }
    e.target.value = '';
  });

  providerSelect.addEventListener('change', updateProviderHint);

  chatHistoryToggle.addEventListener('click', toggleChatHistory);

  // ===== GLOBAL FUNCTIONS =====

  window.toggleChatHistory = toggleChatHistory;

  window.quickCommand = (command) => {
    messageInput.value = command;
    messageInput.focus();
    autoResize();
  };

  window.clearChat = () => {
    if (!confirm('Start a new chat? (Current chat will be saved in history)')) return;

    messagesEl.innerHTML = `
      <div class="welcome-section">
        <div class="welcome-icon">⚡</div>
        <h2 class="welcome-title">Nuclear-Powered AI Laboratory</h2>
        <p class="welcome-subtitle">Unlimited capabilities - No boundaries</p>
        <div class="capabilities">
          <div class="capability">
            <span class="capability-icon">🧠</span>
            <span>Manual Selection</span>
          </div>
          <div class="capability">
            <span class="capability-icon">🎨</span>
            <span>Image Gen</span>
          </div>
          <div class="capability">
            <span class="capability-icon">🎬</span>
            <span>Video Gen</span>
          </div>
          <div class="capability">
            <span class="capability-icon">📄</span>
            <span>All Files</span>
          </div>
          <div class="capability">
            <span class="capability-icon">💰</span>
            <span>Cost Tracking</span>
          </div>
          <div class="capability">
            <span class="capability-icon">🔬</span>
            <span>Research</span>
          </div>
        </div>
      </div>
    `;

    // Start new session
    currentSessionId = `session_${Date.now()}`;
  };

  window.exportChat = async () => {
    try {
      const response = await fetch(`${BACKEND}/chats/history?session_id=${currentSessionId}`);
      const data = await response.json();

      const text = data.map(msg => {
        const date = new Date(msg.ts * 1000);
        return `[${date.toLocaleString()}] ${msg.role.toUpperCase()}: ${msg.content}`;
      }).join('\n\n');

      const format = confirm('Export as DOCX? (OK = DOCX, Cancel = TXT)');

      if (format) {
        const docxResponse = await fetch(`${BACKEND}/files/export/docx`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text })
        });

        const result = await docxResponse.json();
        if (result.ok) {
          const filename = result.filename || result.path.split('/').pop();
          window.open(`${BACKEND}/files/download/${filename}`, '_blank');
          statusText.textContent = 'DOCX exported';
        } else {
          throw new Error('DOCX export failed');
        }
      } else {
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `quantum-ai-chat-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        statusText.textContent = 'TXT exported';
      }

      setTimeout(() => {
        statusText.textContent = 'Online';
      }, 2000);
    } catch (error) {
      alert('Failed to export: ' + error.message);
    }
  };

  // ===== INITIALIZATION =====

  async function init() {
    try {
      const response = await fetch(`${BACKEND}/health`);
      const data = await response.json();

      if (data.status === 'online') {
        statusText.textContent = 'Online';
        statusText.parentElement.querySelector('.status-dot').style.background = 'var(--success)';
        console.log('✅ Backend connected:', data.version);
      }

      const costResponse = await fetch(`${BACKEND}/cost`);
      const costData = await costResponse.json();
      totalCost = costData.total_cost_cents;
      costValue.textContent = formatCost(totalCost);

      // Fetch available providers
      await fetchProviders();

      // Load chat sessions
      await loadChatSessions();

    } catch (error) {
      statusText.textContent = 'Offline';
      statusText.parentElement.querySelector('.status-dot').style.background = 'var(--error)';
      console.error('Failed to connect to backend:', error);
    }

    messageInput.focus();
  }

  init();
  autoResize();

  // Drag & drop support
  document.addEventListener('dragover', (e) => e.preventDefault());
  document.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  console.log('🚀 Quantum AI Lab v5.1 - Nuclear Spaceship initialized!');
  console.log('📍 Current session:', currentSessionId);
})();
