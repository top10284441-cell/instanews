// InstaBonus AI Studio Frontend Application

let currentQueue = [];
let selectedLogoPos = "center";
let uploadedLogoFilename = null;

// 📱 모바일 탭 전환 함수 (발굴/설정 <-> 카드뉴스 보기)
window.switchMobileTab = function(tabName) {
  const sidebar = document.getElementById("sidebar-panel");
  const studio = document.getElementById("studio-panel");
  const btnControls = document.getElementById("btn-tab-controls");
  const btnStudio = document.getElementById("btn-tab-studio");
  
  if (!sidebar || !studio) return;
  
  if (tabName === "studio") {
    sidebar.classList.add("mobile-hide");
    studio.classList.remove("mobile-hide");
    if (btnControls) btnControls.classList.remove("active");
    if (btnStudio) btnStudio.classList.add("active");
  } else {
    studio.classList.add("mobile-hide");
    sidebar.classList.remove("mobile-hide");
    if (btnStudio) btnStudio.classList.remove("active");
    if (btnControls) btnControls.classList.add("active");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadSystemInfo();
  loadQueue();

  // 📱 PC에서 생성한 카드가 스마트폰 화면에 즉시 실시간 동기화 (3초 주기)
  setInterval(syncQueueSilently, 3000);
});

function initEventListeners() {
  // 1. 실행 버튼 (1:1 이미지 순차 변환)
  const btnRun = document.getElementById("btn-run-generate");
  if (btnRun) btnRun.addEventListener("click", () => runAutoCurate(3));

  const btnHarvest = document.getElementById("btn-auto-harvest");
  if (btnHarvest) btnHarvest.addEventListener("click", () => runAutoCurate(3));

  // 1-2. 4대 인스타 채널 탭 원터치 전환 이벤트
  const channelBtns = document.querySelectorAll(".channel-pill-btn, .channel-card-btn");
  channelBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      channelBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const chId = btn.dataset.channel;
      const chName = btn.dataset.name;
      const chHandle = btn.dataset.handle;
      const btnLabel = btn.dataset.btnLabel || `[${chName}] 최신 소재`;

      // 숨은 셀렉트 동기화
      const selChannel = document.getElementById("sel-channel");
      if (selChannel) selChannel.value = chId;

      // 상단 배지 및 발굴 버튼 문구 즉시 변경
      const badgeEl = document.getElementById("current-channel-badge");
      if (badgeEl) {
        const icon = btn.querySelector(".cp-icon, .channel-icon")?.textContent || "🎯";
        badgeEl.textContent = `${icon} ${chHandle}`;
      }

      const btnAuto = document.getElementById("btn-auto-harvest");
      if (btnAuto) btnAuto.textContent = `🚀 ${btnLabel} 3개 자동 발굴`;

      showToast(`🎯 [${chName}] 채널 (${chHandle})이 선택되었습니다.`);
    });
  });

  // 2. 목록 비우기
  const btnClear = document.getElementById("btn-clear-queue");
  if (btnClear) btnClear.addEventListener("click", clearQueue);

  // 3. 로고 위치 세그먼트 버튼
  const segBtns = document.querySelectorAll("#logo-pos-group .seg-btn");
  segBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      segBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      selectedLogoPos = btn.dataset.pos;
    });
  });

  // 4. 로고 업로드 및 제거
  const btnUploadLogo = document.getElementById("btn-upload-logo");
  const logoInput = document.getElementById("logo-file-input");
  if (btnUploadLogo && logoInput) {
    btnUploadLogo.addEventListener("click", () => logoInput.click());
    logoInput.addEventListener("change", handleLogoUpload);
  }

  const btnRemoveLogo = document.getElementById("btn-remove-logo");
  if (btnRemoveLogo) {
    btnRemoveLogo.addEventListener("click", () => {
      uploadedLogoFilename = null;
      const logoText = document.getElementById("input-logo-text");
      if (logoText) logoText.value = "";
      showToast("로고가 제거되었습니다.");
    });
  }

  // 5. 폴더/로컬 사진 업로드 (영상과 1:1 일치)
  const btnFolder = document.getElementById("btn-folder-upload");
  const folderInput = document.getElementById("folder-input");
  const fileInput = document.getElementById("file-input");
  if (btnFolder) {
    btnFolder.addEventListener("click", () => {
      // 폴더 선택 창이 우선 작동하고 없으면 일반 다중 사진 창 작동
      if (folderInput) folderInput.click();
      else if (fileInput) fileInput.click();
    });
  }
  if (folderInput) folderInput.addEventListener("change", handleLocalFiles);
  if (fileInput) fileInput.addEventListener("change", handleLocalFiles);

  // 6. QR 모달
  const btnOpenQr = document.getElementById("btn-open-qr");
  const btnCloseQr = document.getElementById("btn-close-qr");
  const qrModal = document.getElementById("qr-modal");
  if (btnOpenQr && qrModal) {
    btnOpenQr.addEventListener("click", () => qrModal.classList.remove("hidden"));
  }
  if (btnCloseQr && qrModal) {
    btnCloseQr.addEventListener("click", () => qrModal.classList.add("hidden"));
  }
  const btnCopyUrl = document.getElementById("btn-copy-url");
  if (btnCopyUrl) {
    btnCopyUrl.addEventListener("click", () => {
      const urlText = document.getElementById("qr-server-url").textContent;
      navigator.clipboard.writeText(urlText).then(() => showToast("주소가 복사되었습니다!"));
    });
  }

  // 7. 검색 필터
  const searchInput = document.getElementById("input-search");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      renderQueue(currentQueue.filter(item => 
        (item.title || "").toLowerCase().includes(q) || 
        (item.caption || "").toLowerCase().includes(q)
      ));
    });
  }
}

async function loadSystemInfo() {
  try {
    const res = await fetch("/api/info");
    const data = await res.json();
    if (data.server_url) {
      const qrUrl = document.getElementById("qr-server-url");
      if (qrUrl) qrUrl.textContent = data.server_url;
    }
    // 인스타그램 등록 계정 목록 로드
    if (data.channels && data.channels.length > 0) {
      const sel = document.getElementById("sel-channel");
      if (sel) {
        sel.innerHTML = data.channels.map(c => `
          <option value="${c.id}">${c.name || c.id}</option>
        `).join("");
        const activeTab = document.querySelector(".channel-pill-btn.active, .channel-card-btn.active");
        if (activeTab) sel.value = activeTab.dataset.channel;
      }
      const connText = document.getElementById("conn-status-text");
      if (connText) connText.textContent = `${data.channels.length}개 인스타 계정 연결됨`;
    }
  } catch (err) {
    console.error("Failed to load info:", err);
  }
}

let hasAutoSelectedTab = false;

async function loadQueue() {
  try {
    const res = await fetch("/api/queue");
    const data = await res.json();
    currentQueue = data.queue || [];
    renderQueue(currentQueue);

    // 모바일 초기 접속 시 카드가 있으면 바로 '카드뉴스 보기' 탭으로, 없으면 '발굴&설정'으로 이동
    if (!hasAutoSelectedTab && window.innerWidth <= 1024) {
      hasAutoSelectedTab = true;
      const validItems = currentQueue.filter(p => p.status !== "rejected");
      if (validItems.length > 0) {
        switchMobileTab("studio");
      } else {
        switchMobileTab("controls");
      }
    }
  } catch (err) {
    console.error("Queue load error:", err);
  }
}

// 📱 백그라운드 조용한 실시간 동기화 (PC에서 만들면 폰 화면에 자동 갱신)
async function syncQueueSilently() {
  try {
    const res = await fetch("/api/queue");
    const data = await res.json();
    const newQueue = data.queue || [];
    const sigOld = currentQueue.map(p => p.id + p.status + (p.slides ? p.slides.length : 1)).join(",");
    const sigNew = newQueue.map(p => p.id + p.status + (p.slides ? p.slides.length : 1)).join(",");
    if (sigOld !== sigNew) {
      currentQueue = newQueue;
      renderQueue(currentQueue);
    }
  } catch (e) {}
}

function renderQueue(items) {
  const container = document.getElementById("cards-container");
  if (!container) return;

  const validItems = (items || []).filter(p => p.status !== "rejected");

  const countBadge = document.getElementById("mobile-card-count");
  if (countBadge) countBadge.textContent = validItems.length;

  if (!validItems || validItems.length === 0) {
    container.innerHTML = `
      <div class="empty-placeholder">
        <span class="empty-icon">📁</span>
        <h3 style="letter-spacing:1px; color:#8e8e99; font-weight:700;">NO ITEMS TO PROCESS</h3>
        <p style="margin-top:8px;">좌측의 <strong>[📁 폴더 업로드]</strong>로 캡쳐 사진들을 넣거나<br><strong>[⚡ 1:1 이미지 순차 변환]</strong>을 누르면 고화질 카드뉴스가 즉시 제작됩니다.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = validItems.map((post, idx) => {
    const slides = post.slides || [post.image_url];
    const activeSlideIdx = post.active_slide !== undefined ? post.active_slide : 0;
    const currentImgUrl = slides[activeSlideIdx] || post.image_url;
    const isApproved = post.status === "approved";

    const channelMap = {
      today_events: { name: "사건/이슈", handle: "@today.issue.kr", icon: "🏛️" },
      baseball: { name: "한국 야구", handle: "@today.sports.kr", icon: "⚾" },
      animals: { name: "동물/힐링", handle: "@puppy.daily_7", icon: "🐶" },
      celebrity: { name: "한국 연예인", handle: "@star.issue.kr", icon: "⭐" },
      default: { name: "동물/힐링", handle: "@puppy.daily_7", icon: "🐶" }
    };
    const ch = channelMap[post.channel_id] || channelMap[post.category] || { name: post.category || "인스타", handle: "@today.issue.kr", icon: "📌" };

    // 슬라이드 썸네일 버튼 HTML
    const slideButtonsHtml = slides.map((sUrl, sIdx) => `
      <button type="button" class="slide-thumb-btn ${sIdx === activeSlideIdx ? 'active' : ''}" 
              onclick="switchSlide('${post.id}', ${sIdx})" title="${sIdx + 1}번 슬라이드">
        <img src="${sUrl}" alt="슬라이드 ${sIdx + 1}">
      </button>
    `).join("");

    return `
      <div class="story-card" id="card-${post.id}">
        <!-- 상단 툴바 -->
        <div class="card-topbar">
          <div style="display:flex; flex-direction:column; gap:2px;">
            <span class="card-logo-badge" style="display:inline-flex; align-items:center; gap:6px;">
              <span>${ch.icon} ${ch.name}</span>
              <strong style="color:#00ffcc; font-size:11px;">${ch.handle}</strong>
            </span>
          </div>
          <button type="button" class="btn-card-del" title="삭제" onclick="rejectPost('${post.id}')">🗑️</button>
        </div>

        <!-- 메인 미디어 영역 (1:1 고화질 카드뉴스 이미지) -->
        <div class="card-image-wrap" id="media-wrap-${post.id}">
          <img src="${currentImgUrl}" alt="${post.title}" id="main-img-${post.id}" onclick="viewFullImage('${currentImgUrl}')">
        </div>

        <!-- 슬라이드 셀렉터 (1번 표지 / 2번 요약 / + ADD) -->
        <div class="card-slide-selector">
          ${slideButtonsHtml}
          <div class="slide-add-btn" title="슬라이드 추가" onclick="addSlideToPost('${post.id}')">+ ADD</div>
        </div>

        <!-- 캡션 영역 (수정 모드로 리셋 지원) -->
        <div class="card-caption-section">
          <div class="caption-label-row">
            <span class="caption-title">${post.is_editing ? '✏️ 문구 직접 수정 중' : '생성된 본문 (캡션)'}</span>
            ${!post.is_editing ? `
              <button type="button" class="btn-copy-caption" onclick="copyCaption('${post.id}')">
                📋 COPY
              </button>
            ` : ''}
          </div>
          ${post.is_editing ? `
            <div style="background:#191920; border:1px solid #3f3f4a; border-radius:8px; padding:10px; display:flex; flex-direction:column; gap:8px;">
              <div>
                <label style="font-size:11px; font-weight:700; color:#ffe600; display:block; margin-bottom:3px;">제목 수정</label>
                <input type="text" id="edit-title-${post.id}" value="${(post.title || '').replace(/"/g, '&quot;')}" style="width:100%; background:#232328; border:1px solid #3f3f4a; color:#fff; padding:6px 10px; border-radius:6px; font-size:12px; font-weight:700;">
              </div>
              <div>
                <label style="font-size:11px; font-weight:700; color:#ffe600; display:block; margin-bottom:3px;">본문(캡션) 수정</label>
                <textarea id="edit-caption-${post.id}" rows="5" style="width:100%; background:#232328; border:1px solid #3f3f4a; color:#fff; padding:6px 10px; border-radius:6px; font-size:12px; line-height:1.4; resize:vertical;">${post.caption || ''}</textarea>
              </div>
              <div style="display:flex; gap:6px;">
                <button type="button" onclick="saveEditedPost('${post.id}')" style="flex:1; height:32px; background:#00ffcc; color:#000; font-weight:800; border:none; border-radius:6px; font-size:11px; cursor:pointer;">💾 저장 완료</button>
                <button type="button" onclick="toggleEditMode('${post.id}')" style="flex:1; height:32px; background:#2a2a35; color:#fff; font-weight:600; border:none; border-radius:6px; font-size:11px; cursor:pointer;">✕ 취소</button>
              </div>
            </div>
          ` : `
            <div class="caption-preview-box" id="caption-box-${post.id}">${post.caption}</div>
          `}
        </div>

        <!-- 🎛️ 하단 컨트롤 (영상 12:02과 100% 동일) -->
        <div class="card-actions-area">
          <!-- 1. 글자 스타일 및 위치 조정 버튼 -->
          <button type="button" class="btn-toggle-style" onclick="toggleStylePanel('${post.id}')">
            <span>🔤</span> 글자 스타일 및 위치 조정
          </button>

          <!-- 2. 펼쳐지는 세부 스타일 조절 패널 -->
          <div class="style-adjust-panel hidden" id="style-panel-${post.id}">
            <!-- 로고 개별 위치 -->
            <div class="adjust-row">
              <div class="adjust-label">로고 개별 위치</div>
              <div class="pill-choice-row">
                <button type="button" class="pill-choice-btn ${post.logo_position === 'left' ? 'active' : ''}" onclick="updateCardLogoPos('${post.id}', 'left')">왼쪽</button>
                <button type="button" class="pill-choice-btn ${(!post.logo_position || post.logo_position === 'center') ? 'active' : ''}" onclick="updateCardLogoPos('${post.id}', 'center')">중간</button>
                <button type="button" class="pill-choice-btn ${post.logo_position === 'right' ? 'active' : ''}" onclick="updateCardLogoPos('${post.id}', 'right')">오른쪽</button>
              </div>
            </div>

            <!-- 텍스트 위치 조정 (상하좌우 4방향) -->
            <div class="adjust-row">
              <div class="adjust-label">텍스트 위치 조정</div>
              <div class="arrow-pad-grid">
                <button type="button" class="arrow-pad-btn" onclick="nudgeText('${post.id}', 0, -15)" title="위로">↑</button>
                <button type="button" class="arrow-pad-btn" onclick="nudgeText('${post.id}', 0, 15)" title="아래로">↓</button>
                <button type="button" class="arrow-pad-btn" onclick="nudgeText('${post.id}', -15, 0)" title="왼쪽으로">←</button>
                <button type="button" class="arrow-pad-btn" onclick="nudgeText('${post.id}', 15, 0)" title="오른쪽으로">→</button>
              </div>
            </div>

            <!-- 글자 크기 (%) -->
            <div class="adjust-row">
              <div class="adjust-label">글자 크기 (%)</div>
              <div class="size-select-row">
                <select class="size-select-input" onchange="updateFontSize('${post.id}', this.value)">
                  <option value="42" ${post.font_size == 42 ? 'selected' : ''}>6% (작게)</option>
                  <option value="48" ${post.font_size == 48 ? 'selected' : ''}>7% (보통)</option>
                  <option value="54" ${post.font_size == 54 ? 'selected' : ''}>8% (약간 작게)</option>
                  <option value="60" ${post.font_size == 60 ? 'selected' : ''}>9% (크게)</option>
                  <option value="66" ${(!post.font_size || post.font_size == 66) ? 'selected' : ''}>10% (더 크게 - 기본)</option>
                  <option value="74" ${post.font_size == 74 ? 'selected' : ''}>12% (강조)</option>
                </select>
              </div>
            </div>

            <!-- 폰트 굵기 -->
            <div class="adjust-row">
              <div class="adjust-label">폰트 굵기</div>
              <div class="pill-choice-row">
                <button type="button" class="pill-choice-btn ${post.font_weight === 'Bold' ? 'active' : ''}" onclick="updateFontWeight('${post.id}', 'Bold')">Bold</button>
                <button type="button" class="pill-choice-btn ${post.font_weight === 'ExBold' ? 'active' : ''}" onclick="updateFontWeight('${post.id}', 'ExBold')">ExBold</button>
                <button type="button" class="pill-choice-btn ${(!post.font_weight || post.font_weight === 'Black') ? 'active' : ''}" onclick="updateFontWeight('${post.id}', 'Black')">Black</button>
              </div>
            </div>

            <!-- 그라데이션 농도 (어둡게) -->
            <div class="adjust-row">
              <div class="adjust-label">
                <span>그라데이션 농도 (어둡게)</span>
                <span id="grad-opacity-val-${post.id}" style="color:#ffffff; font-weight:700;">${post.grad_opacity !== undefined ? post.grad_opacity : 85}%</span>
              </div>
              <input type="range" class="style-slider" min="0" max="100" value="${post.grad_opacity !== undefined ? post.grad_opacity : 85}"
                     oninput="onGradOpacityInput('${post.id}', this.value)"
                     onchange="updateGradOpacity('${post.id}', this.value)">
            </div>

            <!-- 그라데이션 범위 (높이) -->
            <div class="adjust-row">
              <div class="adjust-label">
                <span>그라데이션 범위 (높이)</span>
                <span id="grad-height-val-${post.id}" style="color:#ffffff; font-weight:700;">${post.grad_height !== undefined ? post.grad_height : 50}%</span>
              </div>
              <input type="range" class="style-slider" min="10" max="100" value="${post.grad_height !== undefined ? post.grad_height : 50}"
                     oninput="onGradHeightInput('${post.id}', this.value)"
                     onchange="updateGradHeight('${post.id}', this.value)">
            </div>
          </div>

          <!-- 3. [🔄 재생성] + [⬆️ 직접 넣기] -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
            <button type="button" class="btn-card-sub" onclick="regenerateCardAI('${post.id}')" style="display:flex; align-items:center; justify-content:center; gap:4px; font-weight:700;">
              <span style="font-size:13px;">🔄</span> 재생성
            </button>
            <button type="button" class="btn-card-sub" onclick="triggerReplaceImage('${post.id}')" style="display:flex; align-items:center; justify-content:center; gap:4px; font-weight:700;">
              <span style="font-size:13px;">⬆️</span> 직접 넣기
            </button>
          </div>
          <input type="file" id="replace-file-${post.id}" accept="image/*" style="display:none;" onchange="handleReplaceFile('${post.id}', event)">

          <!-- 4. [수정 모드로 리셋] + [개별 다운로드] -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
            <button type="button" class="btn-card-sub" onclick="toggleEditMode('${post.id}')" style="display:flex; align-items:center; justify-content:center; gap:4px; font-weight:700;">
              <span style="font-size:13px;">↺</span> 본문 수정
            </button>
            <button type="button" class="btn-card-sub" onclick="downloadImage('${currentImgUrl}')" style="display:flex; align-items:center; justify-content:center; gap:4px; font-weight:700;">
              <span style="font-size:13px;">📥</span> 개별 다운로드
            </button>
          </div>

          <!-- 5. 최종 즉시 전송 버튼 -->
          <button type="button" class="btn-publish-instagram" 
                  onclick="${isApproved ? `window.open('${post.post_url || '#'}', '_blank')` : `approvePost('${post.id}', '${post.channel_id || ''}')`}"
                  style="${isApproved ? 'background:#198754; cursor:pointer;' : ''}">
            ${isApproved ? `✅ ${ch.handle || '인스타'} 발행 완료 (게시물 보기 ↗)` : `🚀 ${ch.handle || '내 인스타'}로 즉시 전송`}
          </button>
        </div>
      </div>
    `;
  }).join("");
}

// 슬라이드 전환 (1번 표지 <-> 2번 본문)
window.switchSlide = function(postId, slideIdx) {
  const post = currentQueue.find(p => p.id === postId);
  if (post && post.slides && post.slides[slideIdx]) {
    post.active_slide = slideIdx;
    const mediaWrap = document.getElementById(`media-wrap-${postId}`);
    if (mediaWrap) {
      mediaWrap.innerHTML = `
        <img src="${post.slides[slideIdx]}" alt="${post.title}" id="main-img-${postId}" onclick="viewFullImage('${post.slides[slideIdx]}')">
      `;
    }
    const cardEl = document.getElementById(`card-${postId}`);
    if (cardEl) {
      cardEl.querySelectorAll(".slide-thumb-btn").forEach((btn, idx) => {
        if (idx === slideIdx) btn.classList.add("active");
        else btn.classList.remove("active");
      });
    }
  }
};

// 수정 모드 토글 (수정 모드로 리셋)
window.toggleEditMode = function(postId) {
  const post = currentQueue.find(p => p.id === postId);
  if (post) {
    post.is_editing = !post.is_editing;
    renderQueue(currentQueue);
  }
};

// 수정 사항 저장
window.saveEditedPost = async function(postId) {
  const post = currentQueue.find(p => p.id === postId);
  if (!post) return;
  const newTitle = document.getElementById(`edit-title-${postId}`)?.value;
  const newCaption = document.getElementById(`edit-caption-${postId}`)?.value;
  if (newTitle !== undefined) post.title = newTitle;
  if (newCaption !== undefined) post.caption = newCaption;
  post.is_editing = false;

  try {
    await fetch("/api/queue/update-post", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId, title: newTitle, caption: newCaption })
    });
    showToast("수정 사항이 저장되었습니다! 💾");
  } catch (e) {
    console.error(e);
  }
  renderQueue(currentQueue);
};

// 🔤 글자 스타일 패널 열기/닫기
window.toggleStylePanel = function(postId) {
  const panel = document.getElementById(`style-panel-${postId}`);
  if (!panel) return;
  panel.classList.toggle("hidden");
};

// 4방향 텍스트 위치 이동 (상하좌우 미세 조정)
window.nudgeText = async function(postId, dx, dy) {
  const post = currentQueue.find(p => p.id === postId);
  if (!post) return;
  post.offset_x = (post.offset_x || 0) + dx;
  post.offset_y = (post.offset_y || 0) + dy;
  await saveStyleAdjustment(post);
};

// 글자 크기 변경
window.updateFontSize = async function(postId, size) {
  const post = currentQueue.find(p => p.id === postId);
  if (!post) return;
  post.font_size = parseInt(size, 10);
  await saveStyleAdjustment(post);
};

// 폰트 굵기 변경 (Bold / ExBold / Black)
window.updateFontWeight = async function(postId, weight) {
  const post = currentQueue.find(p => p.id === postId);
  if (!post) return;
  post.font_weight = weight;
  await saveStyleAdjustment(post);
};

// 로고 개별 위치 변경 (왼쪽 / 중간 / 오른쪽)
window.updateCardLogoPos = async function(postId, pos) {
  const post = currentQueue.find(p => p.id === postId);
  if (!post) return;
  post.logo_position = pos;
  await saveStyleAdjustment(post);
};

// 그라데이션 슬라이더 실시간 숫자 표시 (oninput)
window.onGradOpacityInput = function(postId, val) {
  const label = document.getElementById(`grad-opacity-val-${postId}`);
  if (label) label.innerText = `${val}%`;
};

window.onGradHeightInput = function(postId, val) {
  const label = document.getElementById(`grad-height-val-${postId}`);
  if (label) label.innerText = `${val}%`;
};

// 그라데이션 농도 변경 반영 (onchange)
window.updateGradOpacity = async function(postId, val) {
  const post = currentQueue.find(p => p.id === postId);
  if (!post) return;
  post.grad_opacity = parseInt(val, 10);
  await saveStyleAdjustment(post);
};

// 그라데이션 범위(높이) 변경 반영 (onchange)
window.updateGradHeight = async function(postId, val) {
  const post = currentQueue.find(p => p.id === postId);
  if (!post) return;
  post.grad_height = parseInt(val, 10);
  await saveStyleAdjustment(post);
};

// 서버에 스타일 반영 및 실시간 이미지 갱신
async function saveStyleAdjustment(post) {
  try {
    const res = await fetch("/api/card/adjust-style", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        post_id: post.id,
        offset_x: post.offset_x || 0,
        offset_y: post.offset_y || 0,
        font_size: post.font_size || 66,
        font_weight: post.font_weight || "Black",
        logo_position: post.logo_position || "center",
        grad_opacity: post.grad_opacity !== undefined ? post.grad_opacity : 85,
        grad_height: post.grad_height !== undefined ? post.grad_height : 50
      })
    });
    const data = await res.json();
    if (data.success && data.post) {
      const imgEl = document.getElementById(`main-img-${post.id}`);
      if (imgEl) imgEl.src = data.post.image_url;
      const thumbImg = document.querySelector(`#card-${post.id} .slide-thumb-btn img`);
      if (thumbImg) thumbImg.src = data.post.image_url;
      Object.assign(post, data.post);
    }
  } catch (err) {
    console.error("Style adjust error:", err);
  }
}

// 🔄 [재생성] AI로 해당 카드만 새 제목과 캡션으로 재작성
window.regenerateCardAI = async function(postId) {
  const btn = event.currentTarget;
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = "<span>⏳</span> 생성 중...";
  showToast("AI가 새로운 제목과 본문을 작성 중입니다... (약 10초)");
  try {
    const res = await fetch("/api/card/regenerate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId })
    });
    const data = await res.json();
    if (data.success && data.post) {
      const idx = currentQueue.findIndex(p => p.id === postId);
      if (idx !== -1) currentQueue[idx] = data.post;
      renderQueue(currentQueue);
      showToast("새로운 제목과 캡션으로 재생성되었습니다! ✨");
    } else {
      showToast("재생성 실패");
    }
  } catch (err) {
    showToast(`오류: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
};

// ⬆️ [직접 넣기] 내 사진으로 교체
window.triggerReplaceImage = function(postId) {
  const fileInput = document.getElementById(`replace-file-${postId}`);
  if (fileInput) fileInput.click();
};

window.handleReplaceFile = async function(postId, event) {
  const file = event.target.files[0];
  if (!file) return;
  showToast("선택한 사진으로 카드뉴스를 재합성 중입니다...");
  const formData = new FormData();
  formData.append("post_id", postId);
  formData.append("file", file);
  try {
    const res = await fetch("/api/card/replace-image", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.success && data.post) {
      const idx = currentQueue.findIndex(p => p.id === postId);
      if (idx !== -1) currentQueue[idx] = data.post;
      renderQueue(currentQueue);
      showToast("선택한 사진으로 교체되었습니다! 📸");
    } else {
      showToast("교체 실패");
    }
  } catch (err) {
    showToast(`오류: ${err.message}`);
  }
};

// 슬라이드 사진 추가 (+ ADD)
window.addSlideToPost = function(postId) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("files", file);
    try {
      showToast("새 슬라이드 사진을 분석하여 추가 중...");
      const res = await fetch("/api/upload-and-transform", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.success && data.queue && data.queue.length > 0) {
        const addedPost = data.queue[0];
        const target = currentQueue.find(p => p.id === postId);
        if (target && addedPost.image_url) {
          target.slides = target.slides || [target.image_url];
          target.slides.push(addedPost.image_url);
          renderQueue(currentQueue);
          showToast("새 슬라이드가 추가되었습니다! 📸");
        }
      }
    } catch (err) {
      showToast(`추가 실패: ${err.message}`);
    }
  };
  input.click();
};

// 캡션 복사 (모바일 HTTP 완벽 호환 fallback 지원)
window.copyCaption = function(postId) {
  const post = currentQueue.find(p => p.id === postId);
  if (!post || !post.caption) return;

  const textToCopy = post.caption;
  const onSuccess = () => {
    showToast("📋 캡션 복사 완료! 인스타 앱에 붙여넣으세요. ✍️");
  };

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(textToCopy).then(onSuccess).catch(() => {
      fallbackCopyText(textToCopy, onSuccess);
    });
  } else {
    fallbackCopyText(textToCopy, onSuccess);
  }
};

function fallbackCopyText(text, callback) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  ta.style.top = "-9999px";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand("copy");
    if (callback) callback();
  } catch (err) {
    prompt("아래 캡션 문구를 복사하세요:", text);
  }
  document.body.removeChild(ta);
}

// 폰 갤러리 / PC 다운로드 (모바일 100% 호환 서버 직통 다운로드)
window.downloadImage = function(imgUrl) {
  try {
    showToast("📥 스마트폰에 사진을 저장합니다...");
    const filename = imgUrl.split("/").pop() || "card_1080.jpg";
    const downloadEndpoint = `/api/download?file_path=${encodeURIComponent(imgUrl)}`;

    // 모바일 브라우저(삼성 인터넷, 크롬 등)에서 100% 동작하는 다운로드 방식
    const link = document.createElement("a");
    link.href = downloadEndpoint;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast("🎉 스마트폰에 저장되었습니다! 갤러리(다운로드)를 확인하세요. 📸");
  } catch (e) {
    window.location.href = `/api/download?file_path=${encodeURIComponent(imgUrl)}`;
  }
};

// 원본 확대 보기
window.viewFullImage = function(imgUrl) {
  window.open(imgUrl, "_blank");
};

// 인스타그램 즉시 전송
window.approvePost = async function(postId, cardChannelId) {
  const btn = event.currentTarget;
  const originalText = btn.innerHTML;
  btn.innerHTML = "⏳ 인스타 전송 중...";
  btn.disabled = true;

  // 카드에 지정된 채널 ID 우선 사용
  const targetChannel = cardChannelId || document.getElementById("sel-channel")?.value || "today_events";

  try {
    const res = await fetch("/api/queue/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId, channel_id: targetChannel })
    });
    const data = await res.json();
    if (data.success) {
      showToast("🎉 인스타그램에 성공적으로 전송 업로드되었습니다!");
      loadQueue();
    } else {
      showToast(`⚠️ 전송 실패: ${data.detail || "오류"}`);
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (err) {
    showToast(`통신 오류: ${err.message}`);
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
};

// 포스팅 삭제
window.rejectPost = async function(postId) {
  if (!confirm("이 콘텐츠를 삭제하시겠습니까?")) return;
  try {
    const res = await fetch("/api/queue/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId })
    });
    const data = await res.json();
    if (data.success) {
      showToast("콘텐츠가 완전히 삭제되었습니다. 🗑️");
      currentQueue = data.queue || [];
      renderQueue(currentQueue);
    }
  } catch (err) {
    console.error(err);
  }
};

// AI 순차 변환 실행
async function runAutoCurate(count = 3) {
  const btnRun = document.getElementById("btn-run-generate");
  const btnHarvest = document.getElementById("btn-auto-harvest");
  if (btnRun) {
    btnRun.disabled = true;
    btnRun.innerHTML = "⚡ 생성 중 (약 15초)...";
  }
  if (btnHarvest) {
    btnHarvest.disabled = true;
    btnHarvest.innerHTML = "⏳ AI 뉴스 발굴 중...";
  }

  const lang = document.getElementById("sel-lang") ? document.getElementById("sel-lang").value : "ko";
  const logoText = (document.getElementById("input-logo-text") ? document.getElementById("input-logo-text").value : "").trim();
  const styleSample = document.getElementById("txt-style-sample") ? document.getElementById("txt-style-sample").value : "";
  
  const activeTab = document.querySelector(".channel-pill-btn.active, .channel-card-btn.active");
  const channelId = activeTab ? activeTab.dataset.channel : (document.getElementById("sel-channel")?.value || "today_events");
  const channelName = activeTab ? activeTab.dataset.name : "정치/사건";
  const channelHandle = activeTab ? activeTab.dataset.handle : "@today.issue.kr";

  let categoryName = "사건으로 보는 오늘";
  if (channelId === "animals") categoryName = "동물/힐링";
  else if (channelId === "baseball") categoryName = "스포츠 게시물";
  else if (channelId === "today_events") categoryName = "사건으로 보는 오늘";
  else if (channelId === "celebrity") categoryName = "연예인 게시물";

  showToast(`🚀 [${channelName} ${channelHandle}] 최신 소재를 발굴하여 카드뉴스를 제작 중입니다...`);

  try {
    const res = await fetch("/api/auto-curate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        count: count,
        category: categoryName,
        channel_id: channelId,
        lang: lang,
        logo_text: logoText,
        logo_name: uploadedLogoFilename,
        logo_position: selectedLogoPos,
        style_sample: styleSample
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`✨ ${data.created_count}개의 새로운 바이럴 카드뉴스가 완성되었습니다!`);
      const chkAuto = document.getElementById("chk-auto-publish");
      if (chkAuto && chkAuto.checked && data.queue && data.queue.length > 0) {
        showToast(`🚀 ${channelHandle}로 자동 전송 중...`);
        for (const item of data.queue.slice(0, data.created_count)) {
          try {
            await fetch("/api/queue/approve", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ post_id: item.id, channel_id: channelId })
            });
          } catch (e) {
            console.error(e);
          }
        }
        showToast(`🎉 ${channelHandle}에 자동 전송이 완료되었습니다!`);
      }
      if (window.innerWidth <= 1024) {
        switchMobileTab("studio");
      }
      loadQueue();
    } else {
      showToast(`생성 실패: ${data.detail || "알 수 없는 오류"}`);
    }
  } catch (err) {
    showToast(`오류 발생: ${err.message}`);
  } finally {
    if (btnRun) {
      btnRun.disabled = false;
      btnRun.innerHTML = "⚡ 1:1 이미지 순차 변환";
    }
    if (btnHarvest) {
      btnHarvest.disabled = false;
      const activeTab = document.querySelector(".channel-pill-btn.active, .channel-card-btn.active");
      const btnLabel = activeTab ? (activeTab.dataset.btnLabel || `[${activeTab.dataset.name}] 최신 소재`) : "[정치/사건] 최신 뉴스";
      btnHarvest.innerHTML = `🚀 ${btnLabel} 3개 자동 발굴`;
    }
  }
}

// 목록 비우기
async function clearQueue() {
  if (!confirm("대기열의 모든 콘텐츠를 비우시겠습니까?")) return;
  try {
    await fetch("/api/queue/clear", { method: "POST" });
    showToast("목록을 비웠습니다.");
    loadQueue();
  } catch (err) {
    console.error(err);
  }
}

// 로고 업로드
async function handleLogoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload-logo", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      uploadedLogoFilename = data.filename;
      showToast(`로고 업로드 완료: ${data.filename}`);
    }
  } catch (err) {
    showToast("로고 업로드 실패");
  }
}

// 로컬 파일 업로드 및 자동 카드뉴스 변환
async function handleLocalFiles(e) {
  const files = e.target.files;
  if (!files || files.length === 0) return;

  const btnFolder = document.getElementById("btn-folder-upload");
  const originalText = btnFolder ? btnFolder.innerHTML : "📁 로컬 사진 추가";
  if (btnFolder) {
    btnFolder.disabled = true;
    btnFolder.innerHTML = "⏳ AI 변환 중...";
  }

  showToast(`📸 ${files.length}장의 사진을 분석하여 고화질 카드뉴스로 변환 중입니다... (약 10초)`);

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }
  const selChannel = document.getElementById("sel-channel");
  formData.append("channel_id", selChannel ? selChannel.value : "default");
  formData.append("lang", document.getElementById("sel-lang") ? document.getElementById("sel-lang").value : "ko");
  formData.append("logo_text", (document.getElementById("input-logo-text") ? document.getElementById("input-logo-text").value : "").trim());

  try {
    const res = await fetch("/api/upload-and-transform", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      showToast(`🎉 ${data.created_count}장의 사진이 카드뉴스로 변환되어 대기열에 추가되었습니다!`);
      if (window.innerWidth <= 1024) {
        switchMobileTab("studio");
      }
      loadQueue();
    } else {
      showToast(`변환 실패: ${data.detail || "알 수 없는 오류"}`);
    }
  } catch (err) {
    showToast(`오류 발생: ${err.message}`);
  } finally {
    if (btnFolder) {
      btnFolder.disabled = false;
      btnFolder.innerHTML = originalText;
    }
    e.target.value = "";
  }
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 3000);
}
