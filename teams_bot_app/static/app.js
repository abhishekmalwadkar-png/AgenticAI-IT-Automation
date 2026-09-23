document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const messagesContainer = document.getElementById('messagesContainer');
  const typingIndicator = document.getElementById('typingIndicator');
  const quickChips = document.getElementById('quickChips');
  const resetBtn = document.getElementById('resetBtn');
  const sidebarPreview = document.getElementById('sidebarPreview');
  const ticketBadge = document.getElementById('ticketBadge');
  const ticketDetailsCard = document.getElementById('ticketDetailsCard');
  const telemetryLogs = document.getElementById('telemetryLogs');

  // Tab Navigation Elements
  const tabChatBtn = document.getElementById('tabChatBtn');
  const tabApprovalsBtn = document.getElementById('tabApprovalsBtn');
  const tabAboutBtn = document.getElementById('tabAboutBtn');
  const chatTabView = document.getElementById('chatTabView');
  const approvalsTabView = document.getElementById('approvalsTabView');
  const aboutTabView = document.getElementById('aboutTabView');
  const approvalsBadge = document.getElementById('approvalsBadge');
  const approvalsList = document.getElementById('approvalsList');
  const noApprovalsMsg = document.getElementById('noApprovalsMsg');

  let pendingApprovalsCount = 0;

  // Set welcome time
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  document.getElementById('welcomeTime').textContent = timeStr;

  // Tab Switching
  function switchTab(target) {
    [tabChatBtn, tabApprovalsBtn, tabAboutBtn].forEach(btn => btn.classList.remove('active'));
    [chatTabView, approvalsTabView, aboutTabView].forEach(view => {
      view.style.display = 'none';
      view.classList.remove('active');
    });

    if (target === 'chat') {
      tabChatBtn.classList.add('active');
      chatTabView.style.display = 'flex';
      chatTabView.classList.add('active');
    } else if (target === 'approvals') {
      tabApprovalsBtn.classList.add('active');
      approvalsTabView.style.display = 'flex';
      approvalsTabView.classList.add('active');
    } else if (target === 'about') {
      tabAboutBtn.classList.add('active');
      aboutTabView.style.display = 'flex';
      aboutTabView.classList.add('active');
    }
  }

  tabChatBtn.addEventListener('click', () => switchTab('chat'));
  tabApprovalsBtn.addEventListener('click', () => switchTab('approvals'));
  tabAboutBtn.addEventListener('click', () => switchTab('about'));

  // Event Listeners
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = userInput.value.trim();
    if (!text) return;
    sendMessage(text);
    userInput.value = '';
  });

  quickChips.addEventListener('click', (e) => {
    if (e.target.classList.contains('chip')) {
      const prompt = e.target.getAttribute('data-prompt');
      sendMessage(prompt);
    }
  });

  resetBtn.addEventListener('click', async () => {
    await fetch('/api/reset', { method: 'POST' });
    location.reload();
  });

  function addLog(msg, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = msg;
    telemetryLogs.appendChild(entry);
    telemetryLogs.scrollTop = telemetryLogs.scrollHeight;
  }

  function setStage(stageNum) {
    for (let i = 1; i <= 6; i++) {
      const el = document.getElementById(`step${i}`);
      if (i < stageNum) {
        el.className = 'step-item completed';
      } else if (i === stageNum) {
        el.className = 'step-item active';
      } else {
        el.className = 'step-item';
      }
    }
  }

  function updateServiceNowWidget(ticket) {
    if (!ticket) return;
    ticketBadge.textContent = ticket.status;
    ticketBadge.className = `badge-status ${ticket.status.includes('Closed') ? 'badge-closed' : ticket.status.includes('Approved') ? 'badge-approved' : ticket.status.includes('Escalated') ? 'badge-pending' : 'badge-neutral'}`;

    const linkHtml = ticket.snow_link 
      ? `<a href="${ticket.snow_link}" target="_blank" style="color:#38bdf8; text-decoration:underline; font-weight:700;">${ticket.ticket_number} ↗ (Open in ServiceNow)</a>`
      : ticket.ticket_number;

    ticketDetailsCard.innerHTML = `
      <div class="snow-grid">
        <div class="snow-k">Ticket:</div><div class="snow-v">${linkHtml}</div>
        <div class="snow-k">Type:</div><div class="snow-v">${ticket.request_type}</div>
        <div class="snow-k">Category:</div><div class="snow-v">${ticket.category}</div>
        <div class="snow-k">Priority:</div><div class="snow-v">${ticket.priority}</div>
        <div class="snow-k">Agent:</div><div class="snow-v" style="color:#38bdf8">${ticket.specialized_agent || 'MAF Orchestrator'}</div>
        <div class="snow-k">Execution:</div><div class="snow-v" style="color:#facc15">${ticket.execution_method || 'API / RPA'}</div>
      </div>
    `;
  }

  function appendUserMessage(text) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const row = document.createElement('div');
    row.className = 'message-row user-row';
    row.innerHTML = `
      <div class="msg-avatar user-avatar">AS</div>
      <div class="msg-bubble-group">
        <div class="msg-sender">Aarav Sharma <span class="msg-time">${time}</span></div>
        <div class="msg-bubble user-bubble">${text}</div>
      </div>
    `;
    messagesContainer.appendChild(row);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    sidebarPreview.textContent = `You: ${text}`;
  }

  function appendBotMessage(text, suggestions = []) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const row = document.createElement('div');
    row.className = 'message-row bot-row';

    let chipsHtml = '';
    if (suggestions && suggestions.length > 0) {
      chipsHtml = `<div class="quick-chips" style="margin-top:8px">` +
        suggestions.map(s => `<button class="chip suggestion-chip" data-val="${s}">${s}</button>`).join('') +
        `</div>`;
    }

    row.innerHTML = `
      <div class="msg-avatar bot-avatar">🤖</div>
      <div class="msg-bubble-group">
        <div class="msg-sender">AE Bot <span class="msg-time">${time}</span></div>
        <div class="msg-bubble bot-bubble">
          <p>${text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>')}</p>
          ${chipsHtml}
        </div>
      </div>
    `;
    messagesContainer.appendChild(row);

    // Bind suggestion chips
    row.querySelectorAll('.suggestion-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        sendMessage(btn.getAttribute('data-val'));
      });
    });

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    sidebarPreview.textContent = text.replace(/[*_]/g, '');
  }

  function appendCompletionCard(completionData) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const row = document.createElement('div');
    row.className = 'message-row bot-row';

    const linkHtml = completionData.snow_link
      ? `<a href="${completionData.snow_link}" target="_blank" style="color:#15803d; text-decoration:underline; font-weight:700;">${completionData.ticket_number} (View in ServiceNow)</a>`
      : completionData.ticket_number;

    row.innerHTML = `
      <div class="msg-avatar bot-avatar">🤖</div>
      <div class="msg-bubble-group" style="width: 100%; max-width: 440px;">
        <div class="msg-sender">AE Bot <span class="msg-time">${time}</span></div>
        <div class="card-completed-banner">
          <div style="font-weight:700; font-size:13px; margin-bottom:4px; display:flex; align-items:center; gap:6px;">
            ✅ ${completionData.title}
          </div>
          <div><strong>Ticket Number:</strong> ${linkHtml}</div>
          <div><strong>Request:</strong> ${completionData.request_type}</div>
          <div><strong>Status:</strong> <span style="color:#15803d; font-weight:700;">Closed / Resolved</span></div>
          <div style="margin-top:6px; background:#ffffff; padding:6px 8px; border-radius:4px; border:1px solid #bbf7d0; color:#1e293b;">
            <strong>Resolution:</strong> ${completionData.details}
          </div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(row);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function appendEscalationCard(escalationData) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const row = document.createElement('div');
    row.className = 'message-row bot-row';

    const linkHtml = escalationData.snow_link
      ? `<a href="${escalationData.snow_link}" target="_blank" style="color:#b91c1c; text-decoration:underline; font-weight:700;">${escalationData.ticket_number} (ServiceNow)</a>`
      : escalationData.ticket_number;

    row.innerHTML = `
      <div class="msg-avatar bot-avatar">🤖</div>
      <div class="msg-bubble-group" style="width: 100%; max-width: 440px;">
        <div class="msg-sender">AE Bot <span class="msg-time">${time}</span></div>
        <div style="background:#fef2f2; border:1px solid #f87171; border-radius:6px; padding:12px; color:#991b1b; font-size:12px; line-height:1.4;">
          <div style="font-weight:700; font-size:13px; margin-bottom:4px; display:flex; align-items:center; gap:6px;">
            ⚠️ ${escalationData.title}
          </div>
          <div><strong>Ticket Number:</strong> ${linkHtml}</div>
          <div><strong>Status:</strong> <span style="color:#b91c1c; font-weight:700;">Assigned to Human Tier-2</span></div>
          <div><strong>Queue:</strong> ${escalationData.assigned_to}</div>
          <div style="margin-top:6px; background:#ffffff; padding:6px 8px; border-radius:4px; border:1px solid #fecaca; color:#7f1d1d;">
            <strong>Diagnostic Reason:</strong> ${escalationData.reason}
          </div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(row);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function addApprovalCardToApprovalsTab(ticket) {
    if (noApprovalsMsg) noApprovalsMsg.style.display = 'none';

    pendingApprovalsCount++;
    approvalsBadge.style.display = 'inline-block';
    approvalsBadge.textContent = pendingApprovalsCount;

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const card = document.createElement('div');
    card.className = 'approval-card-item';
    card.id = `approval-card-${ticket.ticket_number}`;

    const linkHtml = ticket.snow_link 
      ? `<a href="${ticket.snow_link}" target="_blank" style="color:#5B5FC7; text-decoration:underline;">${ticket.ticket_number} (ServiceNow)</a>`
      : ticket.ticket_number;

    card.innerHTML = `
      <div class="approval-card-header">
        <div class="approval-card-title">
          <span>📬 Approval Request</span>
          <span class="badge-incident">${ticket.ticket_number}</span>
        </div>
        <span style="font-size:11px; color:#64748b;">${time}</span>
      </div>
      <div class="approval-factset">
        <div class="approval-label">Incident ID:</div><div class="approval-value">${linkHtml}</div>
        <div class="approval-label">Request Type:</div><div class="approval-value"><strong>${ticket.request_type}</strong></div>
        <div class="approval-label">Requested For:</div><div class="approval-value">${ticket.requested_for}</div>
        <div class="approval-label">Scope / Role:</div><div class="approval-value">${ticket.requested_item}</div>
        <div class="approval-label">Approver:</div><div class="approval-value">${ticket.approver}</div>
        <div class="approval-label">Status:</div><div class="approval-value" id="status-val-${ticket.ticket_number}" style="color:#d97706; font-weight:700;">Pending Approval</div>
      </div>
      <div class="card-actions" id="actions-${ticket.ticket_number}">
        <button class="btn-approve" data-ticket="${ticket.ticket_number}">Approve (Execute RPA / Tool)</button>
        <button class="btn-reject" data-ticket="${ticket.ticket_number}">Reject</button>
        <button class="btn-info" data-ticket="${ticket.ticket_number}">Simulate Exception / Human Fallback</button>
      </div>
    `;

    approvalsList.prepend(card);

    // Event listeners
    card.querySelector('.btn-approve').addEventListener('click', () => handleApproval(ticket.ticket_number, 'approve', false));
    card.querySelector('.btn-reject').addEventListener('click', () => handleApproval(ticket.ticket_number, 'reject', false));
    card.querySelector('.btn-info').addEventListener('click', () => handleApproval(ticket.ticket_number, 'approve', true));
  }

  function appendFormCard(adaptiveCard) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const row = document.createElement('div');
    row.className = 'message-row bot-row';
    const formId = `sw-form-${Date.now()}`;

    // Check if official Microsoft Adaptive Card 1.5 JSON schema is provided
    const isAdaptiveCard = adaptiveCard && (adaptiveCard.type === 'AdaptiveCard' || Array.isArray(adaptiveCard.body));

    let title = '📦 Software License & Installation Request';
    let swOptionsHtml = '';
    let verOptionsHtml = '';
    let defaultUser = 'aarav.sharma';
    let userPlaceholder = 'e.g. aarav.sharma / aarav.sharma@company.com';
    let reasonPlaceholder = 'e.g., Required for quarterly financial analysis, reporting dashboards & department project deliverables...';
    let submitTitle = 'Submit Software Request';

    if (isAdaptiveCard) {
      // Parse official Adaptive Card body elements
      adaptiveCard.body.forEach(item => {
        if (item.type === 'TextBlock' && item.size === 'Medium') {
          title = item.text;
        } else if (item.type === 'Input.ChoiceSet') {
          const optionsHtml = (item.choices || []).map(c => 
            `<option value="${c.value || c.title}" ${c.value === item.value ? 'selected' : ''}>${c.title}</option>`
          ).join('');
          if (item.id === 'software_name') swOptionsHtml = optionsHtml;
          if (item.id === 'version') verOptionsHtml = optionsHtml;
        } else if (item.type === 'Input.Text') {
          if (item.id === 'username') {
            if (item.value) defaultUser = item.value;
            if (item.placeholder) userPlaceholder = item.placeholder;
          } else if (item.id === 'reason') {
            if (item.placeholder) reasonPlaceholder = item.placeholder;
          }
        }
      });

      if (adaptiveCard.actions && adaptiveCard.actions.length > 0) {
        submitTitle = adaptiveCard.actions[0].title || submitTitle;
      }
    } else {
      // Fallback for custom lightweight schema
      title = adaptiveCard.title || title;
      swOptionsHtml = (adaptiveCard.software_options || []).map(opt => `<option value="${opt}">${opt}</option>`).join('');
      verOptionsHtml = (adaptiveCard.version_options || []).map(opt => `<option value="${opt}">${opt}</option>`).join('');
    }

    row.innerHTML = `
      <div class="msg-avatar bot-avatar">🤖</div>
      <div class="msg-bubble-group" style="width: 100%; max-width: 440px;">
        <div class="msg-sender">AE Bot <span class="msg-time">${time}</span></div>
        <div class="interactive-form-card" id="${formId}">
          <div class="form-card-header">
            <span>${title}</span>
          </div>
          
          <div class="form-group">
            <label>Select Software Package <span class="req-star">*</span></label>
            <select class="form-select sw-name-select">
              ${swOptionsHtml}
            </select>
          </div>

          <div class="form-group">
            <label>Preferred Version <span class="req-star">*</span></label>
            <select class="form-select sw-version-select">
              ${verOptionsHtml}
            </select>
          </div>

          <div class="form-group">
            <label>Username / Target Account <span class="req-star">*</span></label>
            <input type="text" class="form-input sw-user-input" value="${defaultUser}" placeholder="${userPlaceholder}" />
          </div>

          <div class="form-group">
            <label>Reason for Installation / Business Justification <span class="req-star">*</span></label>
            <textarea class="form-textarea sw-reason-textarea" placeholder="${reasonPlaceholder}"></textarea>
          </div>

          <button class="btn-submit-form">
            <span>${submitTitle}</span> ➔
          </button>
          
          <div class="form-status-container"></div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(row);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    const cardEl = row.querySelector(`#${formId}`);
    const submitBtn = cardEl.querySelector('.btn-submit-form');
    const nameSelect = cardEl.querySelector('.sw-name-select');
    const verSelect = cardEl.querySelector('.sw-version-select');
    const userInput = cardEl.querySelector('.sw-user-input');
    const reasonText = cardEl.querySelector('.sw-reason-textarea');
    const statusContainer = cardEl.querySelector('.form-status-container');

    submitBtn.addEventListener('click', () => {
      const swName = nameSelect.value;
      const swVer = verSelect.value;
      const targetUser = userInput.value.trim() || 'aarav.sharma';
      const reasonVal = reasonText.value.trim() || 'Required for standard business operations';

      // Disable inputs
      submitBtn.disabled = true;
      nameSelect.disabled = true;
      verSelect.disabled = true;
      userInput.disabled = true;
      reasonText.disabled = true;
      submitBtn.style.display = 'none';

      statusContainer.innerHTML = `
        <div class="form-submitted-banner">
          ✓ Request Submitted for ${swName} (${swVer}) - User: ${targetUser}
        </div>
      `;

      submitSoftwareForm({
        software_name: swName,
        version: swVer,
        username: targetUser,
        reason: reasonVal
      });
    });
  }

  async function submitSoftwareForm(formData) {
    appendUserMessage(`Selected: **${formData.software_name}** (${formData.version}) for **${formData.username}**<br/>*Reason: ${formData.reason}*`);
    setStage(1);
    addLog(`[Stage 1] User submitted software form: ${formData.software_name} (${formData.version}) for ${formData.username}`, 'action');

    typingIndicator.style.display = 'flex';
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `Software Request: ${formData.software_name}`,
          software_form: formData
        })
      });

      const data = await res.json();
      typingIndicator.style.display = 'none';

      if (data.reply) {
        appendBotMessage(data.reply);
      }

      if (data.ticket) {
        updateServiceNowWidget(data.ticket);
        addLog(`[Stage 2] Intent extracted. Live incident ${data.ticket.ticket_number} created in ServiceNow!`, 'success');

        if (data.requires_approval) {
          setStage(3);
          addLog(`[Stage 3] Approval card created with Incident ID ${data.ticket.ticket_number} in Approvals tab.`, 'warn');
          addApprovalCardToApprovalsTab(data.ticket);
        } else {
          setStage(2);
        }
      }
    } catch (err) {
      typingIndicator.style.display = 'none';
      appendBotMessage("Sorry, I encountered an error connecting to the MAF backend.");
      addLog(`[Error] ${err.message}`, 'warn');
    }
  }

  async function sendMessage(text) {
    appendUserMessage(text);
    setStage(1);
    addLog(`[Stage 1] End user submitted prompt: "${text}"`, 'action');

    typingIndicator.style.display = 'flex';
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
      });

      const data = await res.json();
      typingIndicator.style.display = 'none';

      if (data.reply) {
        appendBotMessage(data.reply, data.suggestions || []);
      }

      if (data.adaptive_card) {
        appendFormCard(data.adaptive_card);
      } else if (data.form_card) {
        appendFormCard(data.form_card);
      }

      if (data.ticket) {
        updateServiceNowWidget(data.ticket);
        addLog(`[Stage 2] Intent extracted. Live incident ${data.ticket.ticket_number} created in ServiceNow!`, 'success');

        if (data.requires_approval) {
          setStage(3);
          addLog(`[Stage 3] Approval card created with Incident ID ${data.ticket.ticket_number} in Approvals tab.`, 'warn');
          addApprovalCardToApprovalsTab(data.ticket);
        } else {
          setStage(2);
        }
      }
    } catch (err) {
      typingIndicator.style.display = 'none';
      appendBotMessage("Sorry, I encountered an error connecting to the MAF backend.");
      addLog(`[Error] ${err.message}`, 'warn');
    }
  }

  async function handleApproval(ticketId, action, simulateFailure = false) {
    const actionsDiv = document.getElementById(`actions-${ticketId}`);
    const statusVal = document.getElementById(`status-val-${ticketId}`);
    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (action === 'approve') {
      if (actionsDiv) {
        actionsDiv.innerHTML = `<span style="font-size:12px; color:#107c41; font-weight:700;">✓ Approved by Priya Patel at ${timeNow}</span>`;
      }
      if (statusVal) {
        statusVal.textContent = 'Approved';
        statusVal.style.color = '#107c41';
      }
    } else if (action === 'reject') {
      if (actionsDiv) {
        actionsDiv.innerHTML = `<span style="font-size:12px; color:#d83b01; font-weight:700;">✗ Rejected by Priya Patel at ${timeNow}</span>`;
      }
      if (statusVal) {
        statusVal.textContent = 'Rejected';
        statusVal.style.color = '#d83b01';
      }
    }

    if (pendingApprovalsCount > 0) {
      pendingApprovalsCount--;
      if (pendingApprovalsCount === 0) {
        approvalsBadge.style.display = 'none';
      } else {
        approvalsBadge.textContent = pendingApprovalsCount;
      }
    }

    addLog(`[Stage 3] Approver took action: ${action.toUpperCase()} for Incident ${ticketId}.`, 'action');

    try {
      const res = await fetch('/api/approval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket_id: ticketId, action: action, approver: 'Priya Patel (Finance Director)' })
      });
      const data = await res.json();

      if (action === 'approve') {
        updateServiceNowWidget(data.ticket);
        setStage(4);
        addLog(`[Stage 4] ServiceNow approval synced. MAF Orchestrator activated.`, 'info');
        
        // Post confirmation message in the Chat tab
        appendBotMessage(`🔔 **Approval Received**: Incident **${ticketId}** has been **APPROVED** by Priya Patel. MAF Orchestrator is now evaluating and dispatching fulfillment.`);

        // Trigger MAF Stage 4, 5, 6
        triggerMAFExecution(ticketId, simulateFailure);
      } else {
        appendBotMessage(`⚠️ Incident **${ticketId}** was marked as **REJECTED** by Priya Patel.`);
      }
    } catch (err) {
      addLog(`[Error] Approval call failed: ${err.message}`, 'warn');
    }
  }

  async function triggerMAFExecution(ticketId, simulateFailure = false) {
    addLog(`[Stage 4] MAF Orchestrator: Evaluating ticket details, checking SoD policies & constructing dynamic execution plan...`, 'info');
    setStage(4);

    try {
      const res = await fetch(`/api/fulfill/${ticketId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simulate_failure: simulateFailure })
      });
      const data = await res.json();

      setStage(5);
      addLog(`[Stage 5] MAF Orchestrator: Dispatched to specialized agent '${data.plan?.specialized_agent}'. Target Server: '${data.plan?.target_server}'.`, 'action');

      if (data.plan?.steps) {
        data.plan.steps.forEach(st => {
          addLog(`  ↳ ${st}`, 'info');
        });
      }

      if (data.success) {
        setStage(6);
        updateServiceNowWidget(data.ticket);
        addLog(`[Stage 6] Validation Agent: Verification query SUCCESS. Incident ${ticketId} status changed to Resolved (State 6) in ServiceNow.`, 'success');

        // Post chat message notifying that the query has been resolved
        const reqName = data.ticket?.request_type || 'your IT service';
        appendBotMessage(`🎉 **Your query has been resolved!**\n\nYour request for **${reqName}** (Ticket **${ticketId}**) has been successfully fulfilled by AutomationEdge and marked as **Resolved** in ServiceNow.\n\nPlease check and verify. Let me know if you need any further assistance! 👍`);

        appendCompletionCard(data.completion_card);
      } else if (data.escalated) {
        setStage(6);
        updateServiceNowWidget(data.ticket);
        addLog(`[Stage 6] MAF Decision: Exception encountered during T4 RPA execution. Escalated to ${data.escalation?.assigned_to}.`, 'warn');

        appendEscalationCard(data.escalation);
      }
    } catch (err) {
      addLog(`[Error] MAF Execution error: ${err.message}`, 'warn');
    }
  }
});
