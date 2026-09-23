document.addEventListener('DOMContentLoaded', () => {
  // --- DOM ELEMENTS ---
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const messagesContainer = document.getElementById('messagesContainer');
  const typingIndicator = document.getElementById('typingIndicator');
  const quickChips = document.getElementById('quickChips');
  const resetBtn = document.getElementById('resetBtn');
  const personaSelect = document.getElementById('personaSelect');
  const userAvatarInitials = document.getElementById('userAvatarInitials');
  const sidebarPreview = document.getElementById('sidebarPreview');
  const lastMsgTime = document.getElementById('lastMsgTime');

  // Tab Elements
  const tabChatBtn = document.getElementById('tabChatBtn');
  const tabApprovalsBtn = document.getElementById('tabApprovalsBtn');
  const tabCatalogBtn = document.getElementById('tabCatalogBtn');
  const tabObservabilityBtn = document.getElementById('tabObservabilityBtn');
  const railApprovalsBtn = document.getElementById('railApprovalsBtn');

  const chatTabView = document.getElementById('chatTabView');
  const approvalsTabView = document.getElementById('approvalsTabView');
  const catalogTabView = document.getElementById('catalogTabView');
  const observabilityTabView = document.getElementById('observabilityTabView');

  const approvalsBadge = document.getElementById('approvalsBadge');
  const railApprovalsBadge = document.getElementById('railApprovalsBadge');
  const approvalsList = document.getElementById('approvalsList');
  const noApprovalsMsg = document.getElementById('noApprovalsMsg');

  // Observability & Telemetry
  const ticketBadge = document.getElementById('ticketBadge');
  const ticketDetailsCard = document.getElementById('ticketDetailsCard');
  const telemetryLogs = document.getElementById('telemetryLogs');

  // State
  let pendingApprovals = [];
  let currentSender = "Aarav Sharma (Finance Analyst)";

  // Initialize Welcome Time
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const welcomeTime = document.getElementById('welcomeTime');
  if (welcomeTime) welcomeTime.textContent = timeStr;
  if (lastMsgTime) lastMsgTime.textContent = timeStr;

  // --- 1. PERSONA SWITCHER ---
  personaSelect.addEventListener('change', (e) => {
    currentSender = e.target.value;
    if (currentSender.includes("Aarav")) {
      userAvatarInitials.textContent = "AS";
      userAvatarInitials.title = "Aarav Sharma (Requester)";
    } else {
      userAvatarInitials.textContent = "PP";
      userAvatarInitials.title = "Priya Patel (Approver)";
    }
    addLog(`[Persona Switch] Active user is now: ${currentSender}`, 'info');
  });

  // --- 2. TEAMS TAB SWITCHING ---
  function switchTab(target) {
    const tabs = [tabChatBtn, tabApprovalsBtn, tabCatalogBtn, tabObservabilityBtn];
    const views = [chatTabView, approvalsTabView, catalogTabView, observabilityTabView];

    tabs.forEach(t => t && t.classList.remove('active'));
    views.forEach(v => {
      if (v) {
        v.style.display = 'none';
        v.classList.remove('active');
      }
    });

    if (target === 'chat' && tabChatBtn && chatTabView) {
      tabChatBtn.classList.add('active');
      chatTabView.style.display = 'flex';
      chatTabView.classList.add('active');
      scrollToBottom();
    } else if (target === 'approvals' && tabApprovalsBtn && approvalsTabView) {
      tabApprovalsBtn.classList.add('active');
      approvalsTabView.style.display = 'flex';
      approvalsTabView.classList.add('active');
    } else if (target === 'catalog' && tabCatalogBtn && catalogTabView) {
      tabCatalogBtn.classList.add('active');
      catalogTabView.style.display = 'flex';
      catalogTabView.classList.add('active');
    } else if (target === 'observability' && tabObservabilityBtn && observabilityTabView) {
      tabObservabilityBtn.classList.add('active');
      observabilityTabView.style.display = 'flex';
      observabilityTabView.classList.add('active');
    }
  }

  tabChatBtn?.addEventListener('click', () => switchTab('chat'));
  tabApprovalsBtn?.addEventListener('click', () => switchTab('approvals'));
  tabCatalogBtn?.addEventListener('click', () => switchTab('catalog'));
  tabObservabilityBtn?.addEventListener('click', () => switchTab('observability'));
  railApprovalsBtn?.addEventListener('click', () => switchTab('approvals'));

  // Catalog Item Clicks
  document.querySelectorAll('.catalog-item-card').forEach(card => {
    card.addEventListener('click', () => {
      const prompt = card.getAttribute('data-prompt');
      if (prompt) {
        switchTab('chat');
        sendMessage(prompt);
      }
    });
  });

  // Reset Button
  resetBtn.addEventListener('click', async () => {
    try {
      await fetch('/api/reset', { method: 'POST' });
      location.reload();
    } catch {
      location.reload();
    }
  });

  // --- 3. LOGGING & TELEMETRY ---
  function addLog(msg, type = 'info') {
    if (!telemetryLogs) return;
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    entry.textContent = `[${timestamp}] ${msg}`;
    telemetryLogs.appendChild(entry);
    telemetryLogs.scrollTop = telemetryLogs.scrollHeight;
  }

  function setStage(stageNum) {
    for (let i = 1; i <= 6; i++) {
      const el = document.getElementById(`step${i}`);
      if (!el) continue;
      if (i < stageNum) {
        el.className = 'stage-step completed';
      } else if (i === stageNum) {
        el.className = 'stage-step active';
      } else {
        el.className = 'stage-step';
      }
    }
  }

  function updateServiceNowWidget(ticket) {
    if (!ticket || !ticketDetailsCard) return;
    if (ticketBadge) {
      ticketBadge.textContent = ticket.status;
      ticketBadge.className = `badge-status ${ticket.status.includes('Resolved') ? 'badge-approved' : ticket.status.includes('Approval') ? 'badge-pending' : 'badge-neutral'}`;
    }

    const linkHtml = ticket.snow_link 
      ? `<a href="${ticket.snow_link}" target="_blank" style="color:#7B83EB; text-decoration:underline; font-weight:700;">${ticket.ticket_number} ↗ (Open in ServiceNow)</a>`
      : ticket.ticket_number;

    ticketDetailsCard.innerHTML = `
      <div class="snow-grid-view">
        <div class="k">Ticket:</div><div class="v">${linkHtml}</div>
        <div class="k">Request:</div><div class="v">${ticket.request_type || 'IT Request'}</div>
        <div class="k">Category:</div><div class="v">${ticket.category || 'software'}</div>
        <div class="k">Priority:</div><div class="v">${ticket.priority || 'Medium'}</div>
        <div class="k">Agent:</div><div class="v" style="color:#7B83EB">${ticket.specialized_agent || 'MAF Orchestrator'}</div>
        <div class="k">Execution:</div><div class="v" style="color:#FACC15">${ticket.execution_method || 'AutomationEdge RPA'}</div>
      </div>
    `;
  }

  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  // --- 4. MESSAGE RENDERING ---
  function appendUserMessage(text) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const block = document.createElement('div');
    block.className = 'message-block user-block';
    
    const initials = currentSender.includes("Priya") ? "PP" : "AS";

    block.innerHTML = `
      <div class="msg-avatar user-avatar">${initials}</div>
      <div class="msg-body">
        <div class="msg-meta">
          <span class="msg-author">${currentSender.split('(')[0].trim()}</span>
          <span class="msg-timestamp">${time}</span>
        </div>
        <div class="msg-bubble user-bubble">
          <p>${escapeHtml(text)}</p>
        </div>
      </div>
    `;

    messagesContainer.appendChild(block);
    scrollToBottom();
  }

  function appendBotMessage(htmlContent, suggestions = []) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const block = document.createElement('div');
    block.className = 'message-block bot-block';

    let suggestionsHtml = '';
    if (suggestions && suggestions.length > 0) {
      suggestionsHtml = `
        <div class="quick-prompt-chips">
          ${suggestions.map(s => `<button class="teams-chip" data-prompt="${escapeHtml(s)}">${escapeHtml(s)}</button>`).join('')}
        </div>
      `;
    }

    block.innerHTML = `
      <div class="msg-avatar bot-avatar">🤖</div>
      <div class="msg-body">
        <div class="msg-meta">
          <span class="msg-author">AE Bot</span>
          <span class="badge-bot-capsule">BOT</span>
          <span class="msg-timestamp">${time}</span>
        </div>
        <div class="msg-bubble bot-bubble">
          ${formatMarkdown(htmlContent)}
          ${suggestionsHtml}
        </div>
      </div>
    `;

    messagesContainer.appendChild(block);
    
    // Bind click events on suggestions
    block.querySelectorAll('.teams-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        const p = btn.getAttribute('data-prompt');
        if (p) sendMessage(p);
      });
    });

    scrollToBottom();
  }

  // Adaptive Card 1.5 Renderer
  function appendAdaptiveCard(cardPayload) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const block = document.createElement('div');
    block.className = 'message-block bot-block';

    // Parse Adaptive Card body items
    let cardBodyHtml = '';
    const bodyItems = cardPayload.body || [];

    bodyItems.forEach(item => {
      if (item.type === 'TextBlock') {
        const weight = item.weight === 'Bolder' ? 'font-weight:700;' : '';
        const size = item.size === 'Medium' ? 'font-size:14px; margin-bottom:8px;' : 'font-size:12px; margin-bottom:4px;';
        cardBodyHtml += `<p style="${weight} ${size} color:#fff;">${escapeHtml(item.text)}</p>`;
      } else if (item.type === 'Input.ChoiceSet') {
        cardBodyHtml += `
          <div class="adaptive-form-group">
            <label class="adaptive-label">${escapeHtml(item.placeholder || 'Select Option')}</label>
            <select id="${item.id}" class="adaptive-select">
              ${(item.choices || []).map(c => `<option value="${escapeHtml(c.value)}">${escapeHtml(c.title)}</option>`).join('')}
            </select>
          </div>
        `;
      } else if (item.type === 'Input.Text') {
        cardBodyHtml += `
          <div class="adaptive-form-group">
            <label class="adaptive-label">${escapeHtml(item.placeholder || 'Enter value')}</label>
            <input type="${item.isMultiline ? 'text' : 'text'}" id="${item.id}" class="adaptive-input" placeholder="${escapeHtml(item.placeholder || '')}" value="${escapeHtml(item.value || '')}" />
          </div>
        `;
      }
    });

    const submitAction = (cardPayload.actions || []).find(a => a.type === 'Action.Submit') || { title: 'Submit Request' };

    block.innerHTML = `
      <div class="msg-avatar bot-avatar">🤖</div>
      <div class="msg-body">
        <div class="msg-meta">
          <span class="msg-author">AE Bot</span>
          <span class="badge-bot-capsule">BOT</span>
          <span class="msg-timestamp">${time}</span>
        </div>
        <div class="adaptive-card-container">
          <div class="adaptive-card-header">
            <span class="card-icon">📋</span>
            <h4>${escapeHtml(cardPayload.title || 'Microsoft Adaptive Card')}</h4>
          </div>
          <form id="adaptiveCardForm">
            ${cardBodyHtml}
            <button type="submit" class="adaptive-action-btn">${escapeHtml(submitAction.title)}</button>
          </form>
        </div>
      </div>
    `;

    messagesContainer.appendChild(block);

    const form = block.querySelector('#adaptiveCardForm');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const formData = {};
      bodyItems.forEach(item => {
        if (item.id) {
          const el = block.querySelector(`#${item.id}`);
          if (el) formData[item.id] = el.value;
        }
      });
      submitAdaptiveCard(formData);
    });

    scrollToBottom();
  }

  // --- 5. APPROVALS HUB RENDERING ---
  function updateApprovalsBadge() {
    const count = pendingApprovals.filter(a => a.status === 'Awaiting Approval' || a.status === 'Pending Approval').length;
    if (approvalsBadge) {
      approvalsBadge.textContent = count;
      approvalsBadge.style.display = count > 0 ? 'inline-block' : 'none';
    }
    if (railApprovalsBadge) {
      railApprovalsBadge.textContent = count;
      railApprovalsBadge.style.display = count > 0 ? 'inline-block' : 'none';
    }
  }

  function renderApprovalCards() {
    if (!approvalsList) return;
    
    if (pendingApprovals.length === 0) {
      if (noApprovalsMsg) noApprovalsMsg.style.display = 'block';
      return;
    }
    
    if (noApprovalsMsg) noApprovalsMsg.style.display = 'none';
    
    approvalsList.innerHTML = '';
    
    pendingApprovals.forEach(item => {
      const card = document.createElement('div');
      card.className = 'approval-item-card';

      const statusClass = item.status.includes('Approved') ? 'approved' : item.status.includes('Rejected') ? 'rejected' : 'pending';
      const isPending = statusClass === 'pending';

      card.innerHTML = `
        <div class="approval-card-header">
          <div class="approval-title-group">
            <h4 style="font-size:14px; font-weight:700; color:#fff;">${escapeHtml(item.request_type || item.title || 'IT Approval Request')}</h4>
            <span style="font-size:12px; color:#7B83EB; font-weight:600;">#${escapeHtml(item.ticket_number || item.ticket_id)}</span>
          </div>
          <span class="approval-badge ${statusClass}">${escapeHtml(item.status)}</span>
        </div>

        <div class="approval-details-grid">
          <div class="grid-row-k">Requester:</div><div class="grid-row-v">${escapeHtml(item.requested_for || item.requester || 'Aarav Sharma')}</div>
          <div class="grid-row-k">Approver:</div><div class="grid-row-v">${escapeHtml(item.approver || 'Priya Patel (Finance Director)')}</div>
          <div class="grid-row-k">Requested Item:</div><div class="grid-row-v">${escapeHtml(item.requested_item || item.software_spec || 'System Access')}</div>
          <div class="grid-row-k">Priority / SLA:</div><div class="grid-row-v">${escapeHtml(item.priority || 'Medium')} (Target: 8 hrs)</div>
        </div>

        ${isPending ? `
          <div class="approval-actions-bar">
            <button class="btn-reject" data-ticket="${item.ticket_number || item.ticket_id}">Reject</button>
            <button class="btn-approve" data-ticket="${item.ticket_number || item.ticket_id}">Approve Request</button>
          </div>
        ` : `
          <div style="font-size:12px; color:#ADADAD; text-align:right;">
            Status: <strong>${escapeHtml(item.status)}</strong> • Authorization Logged
          </div>
        `}
      `;

      if (isPending) {
        card.querySelector('.btn-approve').addEventListener('click', () => handleApproval(item.ticket_number || item.ticket_id, 'approve'));
        card.querySelector('.btn-reject').addEventListener('click', () => handleApproval(item.ticket_number || item.ticket_id, 'reject'));
      }

      approvalsList.appendChild(card);
    });

    updateApprovalsBadge();
  }

  // --- 6. API COMMUNICATION ---
  async function sendMessage(text) {
    appendUserMessage(text);
    if (typingIndicator) typingIndicator.style.display = 'flex';
    setStage(1);
    addLog(`[MAF Intake] Processing message from ${currentSender}: "${text}"`, 'info');

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          sender: currentSender
        })
      });

      const data = await resp.json();
      if (typingIndicator) typingIndicator.style.display = 'none';

      if (data.stage) setStage(data.stage);

      if (data.ticket) {
        updateServiceNowWidget(data.ticket);
        if (data.requires_approval) {
          pendingApprovals.unshift(data.ticket);
          renderApprovalCards();
          addLog(`[Governance] Approval card routed to Priya Patel for Incident ${data.ticket.ticket_number}`, 'warning');
        } else {
          // Trigger automated fulfillment immediately if no approval required
          triggerFulfillment(data.ticket.ticket_number);
        }
      }

      if (data.adaptive_card || data.form_card) {
        appendAdaptiveCard(data.adaptive_card || data.form_card);
      } else {
        appendBotMessage(data.reply || "Request processed.", data.suggestions || []);
      }

    } catch (err) {
      if (typingIndicator) typingIndicator.style.display = 'none';
      appendBotMessage("⚠️ Error communicating with agent server. Please verify connection.");
      addLog(`[Error] ${err.message}`, 'error');
    }
  }

  async function submitAdaptiveCard(formData) {
    if (typingIndicator) typingIndicator.style.display = 'flex';
    setStage(2);
    addLog(`[MAF Form Intake] Form submitted: ${JSON.stringify(formData)}`, 'info');

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: "Submitted Software Request Form",
          sender: currentSender,
          software_form: formData
        })
      });

      const data = await resp.json();
      if (typingIndicator) typingIndicator.style.display = 'none';

      if (data.stage) setStage(data.stage);

      if (data.ticket) {
        updateServiceNowWidget(data.ticket);
        pendingApprovals.unshift(data.ticket);
        renderApprovalCards();
      }

      appendBotMessage(data.reply || "Form received.", data.suggestions || []);

    } catch (err) {
      if (typingIndicator) typingIndicator.style.display = 'none';
      appendBotMessage("⚠️ Error submitting form. Please try again.");
    }
  }

  async function handleApproval(ticketId, action) {
    addLog(`[Approval] ${currentSender} clicked ${action.toUpperCase()} for Ticket ${ticketId}`, 'info');

    try {
      const resp = await fetch('/api/approval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticket_id: ticketId,
          action: action,
          approver: "Priya Patel (Finance Director)"
        })
      });

      const data = await resp.json();

      const item = pendingApprovals.find(a => (a.ticket_number === ticketId || a.ticket_id === ticketId));
      if (item) {
        item.status = action === 'approve' ? 'Approved' : 'Rejected';
      }
      renderApprovalCards();

      if (action === 'approve') {
        appendBotMessage(`✅ **Approval Confirmed** by **Priya Patel (Finance Director)** for Request **${ticketId}**.\n\n⚙️ *Triggering AutomationEdge RPA orchestration...*`);
        triggerFulfillment(ticketId);
      } else {
        appendBotMessage(`❌ Request **${ticketId}** was **Rejected** by **Priya Patel (Finance Director)**.`);
      }

    } catch (err) {
      addLog(`[Approval Error] ${err.message}`, 'error');
    }
  }

  async function triggerFulfillment(ticketId) {
    setStage(4);
    addLog(`[MAF Orchestrator] Constructing Execution Plan for ${ticketId}...`, 'info');

    try {
      const resp = await fetch(`/api/fulfill/${ticketId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      const data = await resp.json();

      if (data.ticket) {
        updateServiceNowWidget(data.ticket);
      }

      if (data.success) {
        setStage(6);
        addLog(`[Fulfillment Success] AutomationEdge RPA completed. Incident ${ticketId} resolved!`, 'success');
        
        appendBotMessage(`🎉 **Your query has been resolved!**\n\n${data.completion_card?.details || 'Your request has been successfully completed via AutomationEdge RPA.'}\n\nServiceNow Incident: [${ticketId}](${data.ticket?.snow_link || '#'}) status set to **Resolved (6)**.`);
      } else {
        setStage(5);
        addLog(`[Escalation] ${data.ticket?.logs?.[data.ticket?.logs?.length - 1] || 'Fulfillment halted.'}`, 'warning');
        appendBotMessage(`⚠️ Notice for ticket **${ticketId}**: Reassigned for administrative review.`);
      }

    } catch (err) {
      addLog(`[Fulfillment Exception] ${err.message}`, 'error');
    }
  }

  // --- 7. UTILITY HELPERS ---
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let res = text;
    // Bold
    res = res.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    res = res.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Links [title](url)
    res = res.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
    // Newlines to <br> or paragraphs
    res = res.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    return `<p>${res}</p>`;
  }

  // Quick Chips Click Delegation
  quickChips?.addEventListener('click', (e) => {
    if (e.target.classList.contains('teams-chip')) {
      const prompt = e.target.getAttribute('data-prompt');
      if (prompt) sendMessage(prompt);
    }
  });

  // Chat Form Submit
  chatForm?.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = userInput.value.trim();
    if (!text) return;
    sendMessage(text);
    userInput.value = '';
  });

});
