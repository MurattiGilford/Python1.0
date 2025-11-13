(() => {
  'use strict';

  const BACKEND = 'http://127.0.0.1:7861';

  // DOM elements
  const messagesEl = document.getElementById('messages');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const attachBtn = document.getElementById('attachBtn');
  const fileInput = document.getElementById('fileInput');
  const modelHintLabel = document.getElementById('modelHintLabel');
  const currentModelLabel = document.getElementById('currentModelLabel');
  const chatHistoryList = document.getElementById('chatHistoryList');
  const costValue = document.getElementById('costValue');
  const statusText = document.getElementById('statusText');

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

    // Role label
    const roleDiv = document.createElement('div');
    roleDiv.className = 'message-role';
    roleDiv.textContent = messageObj.role === 'user' ? 'You' : 'QAI';

    // Content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Format content with markdown and media
    const formattedContent = formatMessage(messageObj.content, messageObj.metadata?.media_url);
    contentDiv.innerHTML = formattedContent;

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
      contentDiv.appendChild(meta);
    }

    messageDiv.appendChild(roleDiv);
    messageDiv.appendChild(contentDiv);

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
    const messageContent = loadingEl.querySelector('.message-content');

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';

    const text = document.createElement('div');
    text.style.fontStyle = 'italic';
    text.style.marginTop = '8px';
    text.style.fontSize = '12px';
    text.textContent = message;

    messageContent.innerHTML = '';
    messageContent.appendChild(indicator);
    messageContent.appendChild(text);

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
        <div class="chat-dot"></div>
        <div style="flex: 1;">
          <div class="chat-title">${sanitize(session.preview)}</div>
          <div class="chat-date">${dateStr}</div>
        </div>
        <button class="delete-chat-btn" onclick="window.deleteChat('${session.session_id}')" title="Delete chat">✕</button>
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
      console.log('Generating file...');

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
        console.log('File generated successfully');

        // Add success message to chat
        addMessage('assistant', `✅ Generated ${fileType.toUpperCase()} file: ${data.filename}`, {
          model: 'file_generator',
          strategy: 'file_generation'
        });

        window.closeFileGenModal();
      } else {
        const errorMsg = data.error || 'File generation failed';
        alert(`Failed to generate file: ${errorMsg}`);
      }
    } catch (error) {
      console.error('File generation error:', error);
      alert('Failed to generate file: ' + error.message);
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
              <h2 class="welcome-title">How can I help you today?</h2>
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

      console.log('✅ Loaded providers:', Object.keys(providers));

    } catch (error) {
      console.error('Error fetching providers:', error);
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

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

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
      if (costValue) costValue.textContent = formatCost(totalCost);

      if (data.model_used && availableProviders[data.model_used]) {
        const provider = availableProviders[data.model_used];
        if (currentModelLabel) currentModelLabel.textContent = provider.model;
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
    } finally {
      isProcessing = false;
      sendBtn.disabled = false;
      messageInput.focus();
    }
  }

  // ===== FILE UPLOAD - FIXED =====

  async function handleFileUpload(file) {
    if (!file) return;

    console.log(`Uploading ${file.name}...`);

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
        isProcessing = true;
        sendBtn.disabled = true;

        showLoading('Analyzing file...');

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
        if (costValue) costValue.textContent = formatCost(totalCost);

        if (chatData.model_used && availableProviders[chatData.model_used]) {
          const provider = availableProviders[chatData.model_used];
          if (currentModelLabel) currentModelLabel.textContent = provider.model;
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
      console.error('Upload failed:', error);
      alert(`Failed to upload file: ${error.message}`);
      isProcessing = false;
      sendBtn.disabled = false;
    }
  }

  // ===== GLOBAL FUNCTIONS =====

  window.quickCommand = (command) => {
    messageInput.value = command;
    messageInput.focus();
    autoResize();
  };

  window.clearChat = () => {
    if (!confirm('Start a new chat? (Current chat will be saved in history)')) return;

    messagesEl.innerHTML = `
      <div class="welcome-section">
        <h2 class="welcome-title">How can I help you today?</h2>
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
          console.log('DOCX exported successfully');
        } else {
          throw new Error('DOCX export failed');
        }
      } else {
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `qai-chat-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        console.log('TXT exported successfully');
      }
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
        console.log('✅ Backend connected:', data.version);
        if (statusText) statusText.textContent = 'Connected';
      }

      const costResponse = await fetch(`${BACKEND}/cost`);
      const costData = await costResponse.json();
      totalCost = costData.total_cost_cents;
      if (costValue) costValue.textContent = formatCost(totalCost);

      // Fetch available providers
      await fetchProviders();

      // Update model pills after providers are loaded
      updateModelPills();

      // Load chat sessions
      await loadChatSessions();

    } catch (error) {
      console.error('Failed to connect to backend:', error);
      if (statusText) statusText.textContent = 'Disconnected';
    }

    messageInput.focus();
  }

  init();
  autoResize();

  console.log('✨ QAI initialized');
  console.log('📍 Current session:', currentSessionId);

  // ===== MODEL PILL SELECTOR =====
  let selectedProvider = '';

  function updateModelPills() {
    const modelPills = document.getElementById('modelPills');
    if (!modelPills) return;

    // Start with default QAI Sonnet
    let pillsHTML = `
      <div class="model-pill ${selectedProvider === '' ? 'active' : ''}" data-model="QAI Sonnet" data-value="" data-hint="Balanced performance and intelligence">
        <span class="dot"></span>
        <span>QAI Sonnet</span>
      </div>
    `;

    // Add available providers
    for (const [key, provider] of Object.entries(availableProviders)) {
      const isActive = selectedProvider === key ? 'active' : '';
      const hint = `${provider.model} - ${provider.type}`;
      pillsHTML += `
        <div class="model-pill ${isActive}" data-model="${provider.model}" data-value="${key}" data-hint="${hint}">
          <span class="dot"></span>
          <span>${provider.model}</span>
        </div>
      `;
    }

    modelPills.innerHTML = pillsHTML;

    // Attach click handlers
    modelPills.querySelectorAll('.model-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        selectedProvider = pill.getAttribute('data-value');
        const modelName = pill.getAttribute('data-model');
        const modelHint = pill.getAttribute('data-hint');

        // Update UI
        if (currentModelLabel) currentModelLabel.textContent = modelName;
        if (modelHintLabel) modelHintLabel.textContent = modelHint;

        // Update active state
        modelPills.querySelectorAll('.model-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
      });
    });
  }

  // Handle Enter key to send
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea
  messageInput.addEventListener('input', autoResize);

  // Attach file button
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

  // Send button
  sendBtn.addEventListener('click', sendMessage);

  // Drag & drop support
  document.addEventListener('dragover', (e) => e.preventDefault());
  document.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });
})();
