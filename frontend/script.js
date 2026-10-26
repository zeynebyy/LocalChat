let currentChatId = null;
let conversations = {};
let currentSettings = null;

function showError(msg) {
  const errDiv = document.getElementById("error-message");
  if (!errDiv) return;
  errDiv.textContent = msg;
  errDiv.style.display = "block";
  setTimeout(() => {
    errDiv.style.display = "none";
  }, 4000);
}

function handleApiResponse(res) {
  return res.json().then((data) => {
    if (data.error) {
      showError(data.error);
      throw new Error(data.error);
    }
    return data;
  });
}

function scrollChatToBottom() {
  const chatBox = document.getElementById("chat-box");
  chatBox.scrollTop = chatBox.scrollHeight;
}

function addMessage(role, text) {
  const chatBox = document.getElementById("chat-box");
  const msg = document.createElement("div");
  msg.className = `message ${role}`;
  msg.textContent = text;
  chatBox.appendChild(msg);
  scrollChatToBottom();
}
function detectLanguage(text) {
  // Basit Türkçe karakter kontrolü
  return /[çğıöşüÇĞİÖŞÜ]/.test(text) ? "tr" : "en";
}
function cleanBotMessage(msg, lang) {
  // <|assistant|> gibi etiketleri sil
  msg = msg.replace(/<\|assistant\|>/gi, '');
  // Türkçe için baştaki İngilizce başlıkları sil
  if (lang === 'tr') {
    msg = msg.replace(/^Here is a short poem:[^\n]*\n?/i, '');
  }
  // (Translation: ...) veya Çeviri: ... satırlarını sil
  msg = msg.replace(/\(Translation:[^)]+\)/gi, '');
  msg = msg.replace(/Çeviri:[^\n]+/gi, '');
  return msg.trim();
}
function formatPoemIfNeeded(msg, promptText) {
  // promptText'te şiir istendiği anlaşılıyorsa ve cevapta çok virgül varsa, virgülleri satıra çevir
  if (/şiir|dörtlük|poem|verse/i.test(promptText) && (msg.match(/,/g) || []).length >= 2) {
    return msg.split(',').map(s => s.trim()).join('\n');
  }
  return msg;
}
function sendPrompt() {
  const promptEl = document.getElementById("prompt");
  const promptText = promptEl.value.trim();
  if (!promptText) return;

  addMessage("user", promptText);
  promptEl.value = "";
  addMessage("bot", "Yükleniyor...");

  // Her zaman ayarları topla
  let settings = null;
  if (!currentChatId) {
    const saved = localStorage.getItem("pendingSettings");
    if (saved) {
      settings = JSON.parse(saved);
      localStorage.removeItem("pendingSettings");
    }
  } else {
    settings = currentSettings || {};
  }

  // Kullanıcı promptu ve sistem talimatını birleştir
  const userPrompt = settings && settings.behavior ? settings.behavior.split('Sadece kullanıcının dilinde')[0].trim() : '';
  const lang = detectLanguage(promptText);
  let langInstruction = "";
  if (lang === "tr") {
    langInstruction = "Sadece kullanıcının dilinde, kısa ve doğal bir şekilde cevap ver. Asla çeviri, İngilizce açıklama veya başka bir dilde ek bilgi verme. Eğer şiir isteniyorsa, her dizeyi yeni satırda olacak şekilde klasik şiir formatında ver.";
  } else {
    langInstruction = "Answer only in the user's language, briefly and naturally. Never provide translations, English explanations, or any information in another language. If a poem is requested, format it as a classic poem with each line on a new line.";
  }
  if (!settings) settings = {};
  settings.behavior = ((userPrompt || "") + " " + langInstruction).trim();

  fetch("http://127.0.0.1:5000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: promptText,
      conversation_id: currentChatId,
      settings: settings // null değilse gönderilecek
    }),
  })
    .then((res) => handleApiResponse(res))
    .then((data) => {
      let botMsg = data.response || "Yanıt alınamadı.";
      botMsg = cleanBotMessage(botMsg, lang);
      botMsg = formatPoemIfNeeded(botMsg, promptText);
      const convId = data.conversation_id;

      if (!currentChatId) {
        currentChatId = convId;
        conversations[currentChatId] = {
          title: promptText.slice(0, 30),
          messages: [],
          last_time: new Date().toISOString(),
          favorite: false,
          customTitle: false,
        };
        updateChatList();
      }

      if (!conversations[currentChatId].customTitle && conversations[currentChatId].messages.length === 0) {
        conversations[currentChatId].title = promptText.slice(0, 30);
      }

      conversations[currentChatId].messages.push({ role: "user", text: promptText });
      conversations[currentChatId].messages.push({ role: "bot", text: botMsg });
      conversations[currentChatId].last_time = new Date().toISOString();

      document.querySelector(".message.bot:last-child").textContent = botMsg;
      scrollChatToBottom();
    })
    .catch((error) => {
      showError("Sunucu hatası: " + error.message);
      document.querySelector(".message.bot:last-child").textContent = "Sunucu hatası!";
    });
}


function formatDate(timestamp) {
  const date = new Date(timestamp);
  return isNaN(date.getTime()) ? "Tarih yok" : date.toLocaleString("tr-TR");
}

function updateChatList() {
  const chatList = document.getElementById("chat-list");
  chatList.innerHTML = "";
  Object.entries(conversations).forEach(([id, conv]) => {
    const li = document.createElement("li");
    const titleSpan = document.createElement("span");
    titleSpan.innerHTML = `<strong contenteditable="true" onblur="renameConversation('${id}', this.textContent)">${conv.title}</strong><br><small>${formatDate(conv.last_time)}</small>`;
    titleSpan.onclick = () => loadChat(id);

    const actions = document.createElement("div");
    actions.className = "chat-actions";

    const renameBtn = document.createElement("button");
    renameBtn.textContent = "✏️";
    renameBtn.onclick = () => {
      const strong = titleSpan.querySelector("strong");
      strong.focus();
      document.execCommand("selectAll", false, null);
    };

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "🗑️";
    deleteBtn.onclick = () => deleteChat(id);

    const archiveBtn = document.createElement("button");
    archiveBtn.textContent = "📦";
    archiveBtn.onclick = () => archiveChat(id);

    const favoriteBtn = document.createElement("button");
    favoriteBtn.textContent = conv.favorite ? "⭐" : "☆";
    favoriteBtn.onclick = () => {
      const newFav = !conv.favorite;
      fetch(`http://127.0.0.1:5000/conversation/${id}/favorite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ favorite: newFav })
      }).then(() => {
        conversations[id].favorite = newFav;
        updateChatList();
      });
    };

    actions.append(renameBtn, deleteBtn, archiveBtn, favoriteBtn);

    if (conv.archived) {
      const unarchiveBtn = document.createElement("button");
      unarchiveBtn.textContent = "↩️";
      unarchiveBtn.title = "Arşivden çıkar";
      unarchiveBtn.onclick = () => {
        fetch(`http://127.0.0.1:5000/conversation/${id}/archive`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ archived: false })
        }).then(() => {
          delete conversations[id];
          activeBtn.click();
        });
      };
      actions.appendChild(unarchiveBtn);
    }

    li.append(titleSpan, actions);
    chatList.appendChild(li);
  });
}

function renameConversation(id, newTitle) {
  const trimmed = newTitle.trim();
  if (!trimmed) return;

  fetch(`http://127.0.0.1:5000/rename/${id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: trimmed })
  })
  .then(res => res.json())
  .then(() => {
    if (conversations[id]) {
      conversations[id].title = trimmed;
      conversations[id].customTitle = true;
      updateChatList();
    }
  })
  .catch(err => console.error("Başlık güncelleme hatası:", err));
}

function loadChat(id) {
  currentChatId = id;
  const chatBox = document.getElementById("chat-box");
  chatBox.innerHTML = "";
  if (conversations[id]) {
    conversations[id].messages.forEach((msg) => addMessage(msg.role, msg.text));
  }
}

function deleteChat(id) {
  if (!confirm("Silmek istediğinizden emin misiniz?")) return;
  fetch(`http://127.0.0.1:5000/conversation/${id}`, { method: "DELETE" })
    .then((res) => handleApiResponse(res))
    .then(() => {
      delete conversations[id];
      if (currentChatId === id) {
        currentChatId = null;
        document.getElementById("chat-box").innerHTML = "";
      }
      updateChatList();
    })
    .catch((err) => showError("Silme hatası: " + err.message));
}

function archiveChat(id) {
  fetch(`http://127.0.0.1:5000/conversation/${id}/archive`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ archived: true }),
  }).then(() => {
    delete conversations[id];
    updateChatList();
  });
}

function filterMessages() {
  const term = document.getElementById("search-box").value.toLowerCase().trim();
  const chatList = document.getElementById("chat-list");
  chatList.innerHTML = "";

  if (!term) {
    updateChatList(); // Boşsa varsayılan listeyi göster
    return;
  }

  const matched = [];

  Object.entries(conversations).forEach(([id, conv]) => {
    const titleMatch = conv.title.toLowerCase().includes(term);
    const messageMatch = conv.messages?.some(msg =>
      msg.text.toLowerCase().includes(term)
    );

    if (titleMatch || messageMatch) {
      matched.push({ id, conv, priority: titleMatch ? 1 : 2 });
    }
  });

  matched.sort((a, b) => a.priority - b.priority); // Başlık eşleşmeleri öne

  matched.forEach(({ id, conv }) => {
    const li = document.createElement("li");
    const titleSpan = document.createElement("span");
    titleSpan.innerHTML = `<strong contenteditable="true" onblur="renameConversation('${id}', this.textContent)">${conv.title}</strong><br><small>${formatDate(conv.last_time)}</small>`;
    titleSpan.onclick = () => loadChat(id);

    const actions = document.createElement("div");
    actions.className = "chat-actions";

    const renameBtn = document.createElement("button");
    renameBtn.textContent = "✏️";
    renameBtn.onclick = () => {
      const strong = titleSpan.querySelector("strong");
      strong.focus();
      document.execCommand("selectAll", false, null);
    };

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "🗑️";
    deleteBtn.onclick = () => deleteChat(id);

    const archiveBtn = document.createElement("button");
    archiveBtn.textContent = "📦";
    archiveBtn.onclick = () => archiveChat(id);

    const favoriteBtn = document.createElement("button");
    favoriteBtn.textContent = conv.favorite ? "⭐" : "☆";
    favoriteBtn.onclick = () => {
      const newFav = !conv.favorite;
      fetch(`http://127.0.0.1:5000/conversation/${id}/favorite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ favorite: newFav })
      }).then(() => {
        conversations[id].favorite = newFav;
        filterMessages();
      });
    };

    actions.append(renameBtn, deleteBtn, archiveBtn, favoriteBtn);
    li.append(titleSpan, actions);
    chatList.appendChild(li);
  });

  // Eğer eşleşme bulunamazsa kullanıcıya bilgi gösterilebilir
  if (matched.length === 0) {
    const li = document.createElement("li");
    li.textContent = "Eşleşen mesaj bulunamadı.";
    chatList.appendChild(li);
  }
}



window.onload = () => {
  const themeBtn = document.getElementById("toggle-theme");
  const sidebar = document.getElementById("sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const chatSection = document.querySelector(".chat-section");
  const sendBtn = document.getElementById("send-btn");
  const promptInput = document.getElementById("prompt");

  themeBtn.onclick = () => {
    document.body.classList.toggle("dark");
    themeBtn.textContent = document.body.classList.contains("dark") ? "☀️" : "🌙";
    localStorage.setItem("theme", document.body.classList.contains("dark") ? "dark" : "light");
  };

 sidebarToggle.onclick = () => {
  sidebar.classList.toggle("closed");
  chatSection.classList.toggle("panel-open");
  chatSection.classList.toggle("panel-closed");

  // 🔍 Arama kutusunu panel durumuna göre göster/gizle
  const searchBox = document.getElementById("search-box");
  if (sidebar.classList.contains("closed")) {
    searchBox.style.display = "none";
  } else {
    searchBox.style.display = "block";
  }
};


  sendBtn.onclick = sendPrompt;
  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendPrompt();
    }
  });

  document.getElementById("new-chat").onclick = () => {
    currentChatId = null;
    document.getElementById("chat-box").innerHTML = "";
    promptInput.disabled = false;
    promptInput.value = "";
    promptInput.focus();
  };

  document.getElementById("refresh-app").onclick = () => location.reload();

  document.getElementById("show-archived").onclick = () => {
    fetch("http://127.0.0.1:5000/conversations/archived")
      .then(res => handleApiResponse(res))
      .then(list => {
        conversations = {};
        const loadArchived = list.map(conv =>
          fetch(`http://127.0.0.1:5000/conversation/${conv.id}`)
            .then(res => handleApiResponse(res))
            .then(messages => {
              conversations[conv.id] = {
                title: conv.title,
                messages,
                last_time: conv.last_time,
                favorite: conv.favorite || false,
                archived: true
              };
            })
        );
        Promise.all(loadArchived).then(updateChatList);
      });
  };

  document.getElementById("show-favorites").onclick = () => {
    fetch("http://127.0.0.1:5000/conversations/favorites")
      .then(res => handleApiResponse(res))
      .then(list => {
        conversations = {};
        const loadFavs = list.map(conv =>
          fetch(`http://127.0.0.1:5000/conversation/${conv.id}`)
            .then(res => handleApiResponse(res))
            .then(messages => {
              conversations[conv.id] = {
                title: conv.title,
                messages,
                last_time: conv.last_time,
                favorite: conv.favorite || false,
                archived: conv.archived || false
              };
            })
        );
        Promise.all(loadFavs).then(updateChatList);
      });
  };

  const activeBtn = document.getElementById("show-active");
  activeBtn.onclick = () => {
    fetch("http://127.0.0.1:5000/conversations")
      .then(res => handleApiResponse(res))
      .then(list => {
        conversations = {};
        const aktifler = list.filter(c => !c.archived);
        const loadActive = aktifler.map(conv =>
          fetch(`http://127.0.0.1:5000/conversation/${conv.id}`)
            .then(res => handleApiResponse(res))
            .then(messages => {
              conversations[conv.id] = {
                title: conv.title,
                messages,
                last_time: conv.last_time,
                favorite: conv.favorite || false,
                archived: false
              };
            })
        );
        Promise.all(loadActive).then(() => {
          updateChatList();
          if (aktifler.length > 0) {
            const lastConvId = aktifler[aktifler.length - 1].id;
            currentChatId = lastConvId;
            loadChat(lastConvId);
          }
        });
      });
  };

  activeBtn.click();
  // Sayfa ilk açıldığında prompt alanını aktif ve odaklı yap
  promptInput.disabled = false;
  promptInput.focus();
};
function saveSettings() {
  const promptEl = document.getElementById("prompt");
  const userPrompt = document.getElementById("system-behavior").value || "";
  const temperature = parseFloat(document.getElementById("temperature").value);
  const top_p = parseFloat(document.getElementById("top_p").value);
  const top_k = parseInt(document.getElementById("top_k").value);
  const repetition_penalty = parseFloat(document.getElementById("repetition_penalty").value);

  if (isNaN(temperature) || isNaN(top_p) || isNaN(top_k) || isNaN(repetition_penalty)) {
    alert("Lütfen tüm sayısal ayarları doldurun.");
    return;
  }

  // Sistem davranış talimatını birleştir
  const langInstruction = "Sadece kullanıcının dilinde, kısa ve doğal bir şekilde cevap ver. Asla çeviri, İngilizce açıklama veya başka bir dilde ek bilgi verme. Eğer şiir isteniyorsa, her dizeyi yeni satırda olacak şekilde klasik şiir formatında ver.";
  const behavior = (userPrompt + " " + langInstruction).trim();

  const newSettings = {
    behavior,
    temperature,
    top_p,
    top_k,
    repetition_penalty
  };

  if (!currentChatId) {
    // Henüz sohbet yoksa localStorage'a yaz
    localStorage.setItem("pendingSettings", JSON.stringify(newSettings));
    currentSettings = newSettings;
    alert("Ayarlar kaydedildi! Artık mesaj göndererek sohbeti başlatabilirsiniz.");
    document.getElementById("settings-panel").style.display = "none";

    // Zorla etkinleştir ve focus ver
    setTimeout(() => {
      if (promptEl) {
        promptEl.disabled = false;
        promptEl.readOnly = false;
        promptEl.value = "";
        promptEl.focus();
      }
    }, 100);

    return;
  }

  // Eğer aktif sohbet varsa veritabanına kaydet
  fetch(`http://127.0.0.1:5000/settings/${currentChatId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(newSettings)
  })
    .then(res => {
      if (!res.ok) throw new Error("Ayarlar gönderilemedi.");
      return res.json();
    })
    .then(() => {
      alert("Ayarlar başarıyla kaydedildi!");
      currentSettings = newSettings;
      document.getElementById("settings-panel").style.display = "none";

      // Zorla yeniden aktif yap ve odakla
      setTimeout(() => {
        if (promptEl) {
          promptEl.disabled = false;
          promptEl.readOnly = false;
          promptEl.value = "";
          promptEl.focus();
        }
      }, 100);
    })
    .catch(err => {
      console.error("Ayar gönderme hatası:", err);
      alert("Ayarlar gönderilirken hata oluştu.");
    });
}

// Ayarlar paneli kapanınca prompt alanını zorla aktif ve odaklı yap
const settingsPanel = document.getElementById("settings-panel");
if (settingsPanel) {
  const observer = new MutationObserver(() => {
    if (settingsPanel.style.display === "none") {
      setTimeout(() => {
        const promptEl = document.getElementById("prompt");
        if (promptEl) {
          promptEl.disabled = false;
          promptEl.readOnly = false;
          promptEl.value = "";
          promptEl.focus();
        }
      }, 100);
    }
  });
  observer.observe(settingsPanel, { attributes: true, attributeFilter: ["style"] });
}
