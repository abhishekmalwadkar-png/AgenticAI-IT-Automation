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

  // Activity Bell & Flyout
  const topActivityBell = document.getElementById('topActivityBell');
  const topBellBadge = document.getElementById('topBellBadge');
  const activityFlyout = document.getElementById('activityFlyout');
  const activityFeedList = document.getElementById('activityFeedList');
  const emptyActivityMsg = document.getElementById('emptyActivityMsg');
  const flyoutCount = document.getElementById('flyoutCount');
  const railActivityBtn = document.getElementById('railActivityBtn');
  const railActivityBadge = document.getElementById('railActivityBadge');

  // Sidebar Chats
  const chatItemApprovals = document.getElementById('chatItemApprovals');
  const chatItemBot = document.getElementById('chatItemBot');
  const chatItemPriya = document.getElementById('chatItemPriya');
  const chatItemHelpdesk = document.getElementById('chatItemHelpdesk');
  const approvalChatTime = document.getElementById('approvalChatTime');
  const approvalChatPreview = document.getElementById('approvalChatPreview');

  // Tabs
  const tabChatBtn = document.getElementById('tabChatBtn');
  const tabCatalogBtn = document.getElementById('tabCatalogBtn');
  const tabObservabilityBtn = document.getElementById('tabObservabilityBtn');

  const chatTabView = document.getElementById('chatTabView');
  const catalogTabView = document.getElementById('catalogTabView');
  const observabilityTabView = document.getElementById('observabilityTabView');

  // Observability & Telemetry
  const ticketBadge = document.getElementById('ticketBadge');
  const ticketDetailsCard = document.getElementById('ticketDetailsCard');
  const telemetryLogs = document.getElementById('telemetryLogs');

  // State
  let pendingApprovals = [];
  let currentSender = "Aarav Sharma (Finance Analyst)";
  let activeChat = "bot"; // "bot" or "approvals"

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

  // --- 2. ACTIVITY BELL FLYOUT TOGGLE ---
  function toggleActivityFlyout(e) {
    if (e) e.stopPropagation();
    const isVisible = activityFlyout.style.display === 'block';
    activityFlyout.style.display = isVisible ? 'none' : 'block';
  }

  topActivityBell?.addEventListener('click', toggleActivityFlyout);
  railActivityBtn?.addEventListener('click', (e) => {
    toggleActivityFlyout(e);
  });

  // Close flyout when clicking anywhere outside
  document.addEventListener('click', (e) => {
    if (activityFlyout && !activityFlyout.contains(e.target) && !topActivityBell.contains(e.target) && !railActivityBtn.contains(e.target)) {
      activityFlyout.style.display = 'none';
    }
  });

  // --- 3. TEAMS TAB SWITCHING ---
  function switchTab(target) {
    const tabs = [tabChatBtn, tabCatalogBtn, tabObservabilityBtn];
    const views = [chatTabView, catalogTabView, observabilityTabView];

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
  tabCatalogBtn?.addEventListener('click', () => switchTab('catalog'));
  tabObservabilityBtn?.addEventListener('click', () => switchTab('observability'));

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
  resetBtn?.addEventListener('click', async () => {
    try {
      await fetch('/api/reset', { method: 'POST' });
      location.reload();
    } catch {
      location.reload();
    }
  });

  // Sidebar Chats Selection
  chatItemBot?.addEventListener('click', () => {
    setActiveConversation('bot');
  });

  chatItemApprovals?.addEventListener('click', () => {
    setActiveConversation('approvals');
  });

  function setActiveConversation(conv) {
    activeChat = conv;
    if (conv === 'bot') {
      chatItemBot.classList.add('active');
      chatItemApprovals.classList.remove('active');
    } else {
      chatItemApprovals.classList.add('active');
      chatItemBot.classList.remove('active');
      // Persona automatically hints to Approver
      personaSelect.value = "Priya Patel (Finance Director)";
      currentSender = personaSelect.value;
      userAvatarInitials.textContent = "PP";
      userAvatarInitials.title = "Priya Patel (Approver)";
    }
    switchTab('chat');
  }

  // --- 4. LOGGING & TELEMETRY ---
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

  // --- 5. NOTIFICATION & APPROVALS ROUTING (BELL ICON & NEW CHAT) ---
  function updateActivityBellNotifications() {
    const activePending = pendingApprovals.filter(a => a.status === 'Awaiting Approval' || a.status === 'Pending Approval');
    const count = activePending.length;

    // Update Badges on Bell icons
    if (topBellBadge) {
      topBellBadge.textContent = count;
      topBellBadge.style.display = count > 0 ? 'inline-block' : 'none';
    }
    if (railActivityBadge) {
      railActivityBadge.textContent = count;
      railActivityBadge.style.display = count > 0 ? 'inline-block' : 'none';
    }
    if (flyoutCount) {
      flyoutCount.textContent = `${count} pending`;
    }

    // Update Activity Flyout List
    if (count === 0) {
      activityFeedList.innerHTML = `
        <div class="empty-flyout" id="emptyActivityMsg">
          <p>No new approval notifications.</p>
        </div>
      `;
      return;
    }

    activityFeedList.innerHTML = '';
    activePending.forEach(item => {
      const flyoutItem = document.createElement('div');
      flyoutItem.className = 'flyout-item unread';
      const ticketNum = item.ticket_number || item.ticket_id;
      const reqType = item.request_type || item.title || 'IT Approval';
      const requester = item.requested_for || item.requester || 'Aarav Sharma';
      const targetItem = item.requested_item || item.software_spec || 'System Access';

      flyoutItem.innerHTML = `
        <div class="flyout-item-header">
          <div class="flyout-item-title">🔔 Approval Requested</div>
          <div class="flyout-item-time">Just now</div>
        </div>
        <div class="flyout-item-desc">
          <strong>${escapeHtml(requester)}</strong> requested <strong>${escapeHtml(targetItem)}</strong> (${escapeHtml(reqType)} • #${escapeHtml(ticketNum)}).
        </div>
        <div class="flyout-actions">
          <button class="flyout-btn-reject" data-ticket="${ticketNum}">Reject</button>
          <button class="flyout-btn-approve" data-ticket="${ticketNum}">Approve</button>
        </div>
      `;

      flyoutItem.querySelector('.flyout-btn-approve').addEventListener('click', (e) => {
        e.stopPropagation();
        handleApproval(ticketNum, 'approve');
        activityFlyout.style.display = 'none';
      });

      flyoutItem.querySelector('.flyout-btn-reject').addEventListener('click', (e) => {
        e.stopPropagation();
        handleApproval(ticketNum, 'reject');
        activityFlyout.style.display = 'none';
      });

      activityFeedList.appendChild(flyoutItem);
    });

    // Light up the Approvals conversation item in the sidebar
    if (chatItemApprovals) {
      chatItemApprovals.style.display = 'flex';
      const latest = activePending[0];
      if (latest && approvalChatPreview) {
        approvalChatPreview.textContent = `Action Required: Approve ${latest.request_type || 'Access'} (#${latest.ticket_number || latest.ticket_id})`;
      }
      if (approvalChatTime) {
        approvalChatTime.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
    }
  }

  // --- 6. IN-CHAT APPROVAL ADAPTIVE CARD (FLUENT 2 DESIGN) ---
  function appendInChatApprovalCard(ticket) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const block = document.createElement('div');
    block.className = 'message-block bot-block';
    const ticketNum = ticket.ticket_number || ticket.ticket_id;
    const reqType = ticket.request_type || 'IT Access Request';
    const requester = ticket.requested_for || ticket.requester || 'Aarav Sharma';
    const approver = ticket.approver || 'Priya Patel (Finance Director)';
    const itemSpec = ticket.requested_item || ticket.software_spec || 'SAP S/4HANA Finance Authorization';

    block.innerHTML = `
      <div class="msg-avatar bot-avatar">🤖</div>
      <div class="msg-body">
        <div class="msg-meta">
          <span class="msg-author">AE Bot</span>
          <span class="badge-bot-capsule">BOT</span>
          <span class="msg-timestamp">${time}</span>
        </div>
        <div class="in-chat-approval-card" id="card-${ticketNum}">
          <div class="in-chat-approval-header">
            <div class="title-badge-group">
              <span style="font-size:16px;">📬</span>
              <h4>Action Required: ${escapeHtml(reqType)}</h4>
            </div>
            <span class="approval-badge pending" id="badge-${ticketNum}">Pending Approval</span>
          </div>

          <div class="in-chat-approval-grid">
            <div class="k">Incident:</div>
            <div class="v">
              <a href="${ticket.snow_link || '#'}" target="_blank" style="color:#7B83EB; text-decoration:underline;">
                #${escapeHtml(ticketNum)} (ServiceNow)
              </a>
            </div>
            <div class="k">Requester:</div><div class="v">${escapeHtml(requester)}</div>
            <div class="k">Approver:</div><div class="v">${escapeHtml(approver)}</div>
            <div class="k">Target Item:</div><div class="v">${escapeHtml(itemSpec)}</div>
            <div class="k">Security SLA:</div><div class="v">High • Standard 8h window</div>
          </div>

          <div class="in-chat-approval-actions" id="actions-${ticketNum}">
            <button class="in-chat-btn-reject" id="btnReject-${ticketNum}">
              ✕ Reject Request
            </button>
            <button class="in-chat-btn-approve" id="btnApprove-${ticketNum}">
              ✓ Approve Request
            </button>
          </div>
        </div>
      </div>
    `;

    messagesContainer.appendChild(block);

    // Bind approve/reject events
    block.querySelector(`#btnApprove-${ticketNum}`).addEventListener('click', () => {
      handleApproval(ticketNum, 'approve');
    });

    block.querySelector(`#btnReject-${ticketNum}`).addEventListener('click', () => {
      handleApproval(ticketNum, 'reject');
    });

    scrollToBottom();
  }

  // --- 7. MESSAGE RENDERING ---
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

  // Adaptive Card 1.5 Form Renderer
  function appendAdaptiveCard(cardPayload) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const block = document.createElement('div');
    block.className = 'message-block bot-block';

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
            <input type="text" id="${item.id}" class="adaptive-input" placeholder="${escapeHtml(item.placeholder || '')}" value="${escapeHtml(item.value || '')}" />
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

  // --- 8. API COMMUNICATION ---
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
          updateActivityBellNotifications();
          addLog(`[Governance] Approval routed to Bell Icon & Approvals Hub for Incident ${data.ticket.ticket_number}`, 'warning');
          // In-Chat Approval Card
          appendInChatApprovalCard(data.ticket);
        } else {
          // Trigger automated fulfillment immediately if auto-approved
          triggerFulfillment(data.ticket.ticket_number);
        }
      }

      if (data.adaptive_card || data.form_card) {
        appendAdaptiveCard(data.adaptive_card || data.form_card);
      } else if (data.reply) {
        appendBotMessage(data.reply, data.suggestions || []);
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
        updateActivityBellNotifications();
        appendInChatApprovalCard(data.ticket);
      }

      if (data.reply) {
        appendBotMessage(data.reply, data.suggestions || []);
      }

    } catch (err) {
      if (typingIndicator) typingIndicator.style.display = 'none';
      appendBotMessage("⚠️ Error submitting form. Please try again.");
    }
  }

  async function handleApproval(ticketId, action) {
    addLog(`[Approval] Priya Patel (Approver) clicked ${action.toUpperCase()} for Ticket ${ticketId}`, 'info');

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

      // Update In-Chat Card UI
      const cardEl = document.getElementById(`card-${ticketId}`);
      const badgeEl = document.getElementById(`badge-${ticketId}`);
      const actionsEl = document.getElementById(`actions-${ticketId}`);

      if (cardEl && badgeEl && actionsEl) {
        if (action === 'approve') {
          cardEl.classList.remove('rejected');
          cardEl.classList.add('approved');
          badgeEl.className = 'approval-badge approved';
          badgeEl.textContent = 'Approved';
          actionsEl.innerHTML = `
            <div class="approval-status-stamp approved">
              ✓ Approved by Priya Patel (${new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})})
            </div>
          `;
        } else {
          cardEl.classList.add('rejected');
          badgeEl.className = 'approval-badge rejected';
          badgeEl.textContent = 'Rejected';
          actionsEl.innerHTML = `
            <div class="approval-status-stamp rejected">
              ✕ Rejected by Priya Patel (${new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})})
            </div>
          `;
        }
      }

      // Update Bell Notification badges
      updateActivityBellNotifications();

      if (action === 'approve') {
        appendBotMessage(`✅ **Approval Confirmed** by **Priya Patel (Finance Director)** for Request **#${ticketId}**.\n\n⚙️ *Triggering AutomationEdge RPA orchestration...*`);
        triggerFulfillment(ticketId);
      } else {
        appendBotMessage(`❌ Request **#${ticketId}** was **Rejected** by **Priya Patel (Finance Director)**.`);
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

  // --- 9. UTILITY HELPERS ---
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
    res = res.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    res = res.replace(/\*(.*?)\*/g, '<em>$1</em>');
    res = res.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
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
