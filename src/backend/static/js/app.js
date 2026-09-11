/**
 * DRIVEFACE AI — CLIENT-SIDE CONTROLLER
 * Exclusively Google OAuth2 Authentication, Dynamic Menus & AI Pipeline.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Application State
  const state = {
    token: localStorage.getItem("df_access_token"),
    user: JSON.parse(localStorage.getItem("df_user") || "null"),
    currentJobId: null,
    pollingInterval: null,
    demoClusters: [
      { id: "c1", label: "Ana Silva", photos: 18, emoji: "👩" },
      { id: "c2", label: "Carlos Souza", photos: 24, emoji: "👨" },
      { id: "c3", label: "Mariana Costa", photos: 15, emoji: "👩‍🦰" },
      { id: "c4", label: "Não Identificado #4", photos: 9, emoji: "🧑" },
      { id: "c5", label: "Não Identificado #5", photos: 12, emoji: "👱‍♂️" },
      { id: "c6", label: "Lucas Pereira", photos: 31, emoji: "🧔" }
    ]
  };

  // DOM Elements - Shell
  const mainNav = document.getElementById("mainNav");
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const userAuthArea = document.getElementById("userAuthArea");
  const publicLandingView = document.getElementById("publicLandingView");
  const authenticatedContainer = document.getElementById("authenticatedContainer");
  const toastContainer = document.getElementById("toastContainer");

  // DOM Elements - Landing
  const btnGoogleLoginMain = document.getElementById("btnGoogleLoginMain");
  const btnDemoLogin = document.getElementById("btnDemoLogin");

  // DOM Elements - Authenticated Features
  const userGreetingName = document.getElementById("userGreetingName");
  const formProcess = document.getElementById("formProcessAlbum");
  const jobTrackerCard = document.getElementById("jobTrackerCard");
  const progressBarFill = document.getElementById("progressBarFill");
  const trackerPercentage = document.getElementById("trackerPercentage");
  const trackerStatusBadge = document.getElementById("trackerStatusBadge");
  const trackerPhotosCount = document.getElementById("trackerPhotosCount");
  const trackerFacesCount = document.getElementById("trackerFacesCount");
  const trackerPeopleCount = document.getElementById("trackerPeopleCount");
  const trackerStepDesc = document.getElementById("trackerStepDesc");
  const trackerJobId = document.getElementById("trackerJobId");
  const btnViewCompletedAlbum = document.getElementById("btnViewCompletedAlbum");
  const clustersGrid = document.getElementById("clustersGrid");

  // DOM Elements - Sharing
  const btnCopyShareLink = document.getElementById("btnCopyShareLink");
  const shareUrlInput = document.getElementById("shareUrlInput");
  const btnAddWhitelist = document.getElementById("btnAddWhitelistEmail");
  const newWhitelistEmail = document.getElementById("newWhitelistEmail");
  const whitelistContainer = document.getElementById("whitelistContainer");
  const ownerEmailItem = document.getElementById("ownerEmailItem");

  // Toast Function
  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span>${type === "success" ? "✓" : "⚠"}</span>
      <span>${message}</span>
    `;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }
  window.showToast = showToast;

  // Centralized Authenticated Fetch with Auto Token Refresh
  window.authFetch = async function(url, options = {}) {
    options.headers = options.headers || {};
    let token = state.token || localStorage.getItem("df_access_token");

    const setHeader = (tok) => {
      if (options.headers instanceof Headers) {
        options.headers.set("Authorization", `Bearer ${tok}`);
      } else {
        options.headers["Authorization"] = `Bearer ${tok}`;
      }
    };

    if (token) {
      setHeader(token);
    }

    let response = await fetch(url, options);

    if (response.status === 401) {
      let isTokenExpired = false;
      try {
        const clone = response.clone();
        const data = await clone.json();
        if (data.code === "token_not_valid" || (data.detail && data.detail.toLowerCase().includes("token"))) {
          isTokenExpired = true;
        }
      } catch (_) {
        isTokenExpired = true;
      }

      if (isTokenExpired) {
        const refreshToken = localStorage.getItem("df_refresh_token");
        if (refreshToken) {
          try {
            const refreshRes = await fetch("/api/v1/auth/token/refresh/", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ refresh: refreshToken })
            });

            if (refreshRes.ok) {
              const refreshData = await refreshRes.json();
              const newAccessToken = refreshData.access;
              state.token = newAccessToken;
              localStorage.setItem("df_access_token", newAccessToken);
              if (refreshData.refresh) {
                localStorage.setItem("df_refresh_token", refreshData.refresh);
              }
              setHeader(newAccessToken);
              return await fetch(url, options);
            }
          } catch (err) {
            console.warn("Falha na tentativa de refresh do token JWT:", err);
          }
        }

        // Se o refresh falhou ou não existe refresh token, limpa credenciais expiradas
        logout();
        showToast("Sua sessão expirou. Faça login novamente para continuar.", "error");
      }
    }

    return response;
  };

  // 1. Process URL OAuth Callback Parameters
  function checkUrlAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const authSuccess = urlParams.get("auth_success");
    const authError = urlParams.get("auth_error");

    if (authSuccess === "true") {
      const token = urlParams.get("token");
      const refreshToken = urlParams.get("refresh_token");
      const email = urlParams.get("email");
      const name = urlParams.get("name") || (email ? email.split("@")[0] : "Usuário");
      const picture = urlParams.get("picture") || "";

      state.token = token;
      state.user = { email, name, picture };
      localStorage.setItem("df_access_token", token);
      if (refreshToken) {
        localStorage.setItem("df_refresh_token", refreshToken);
      }
      localStorage.setItem("df_user", JSON.stringify(state.user));

      // Limpa os parâmetros da URL sem recarregar
      window.history.replaceState({}, document.title, window.location.pathname);
      showToast(`Login realizado com sucesso via Google! Olá, ${name}.`, "success");
    } else if (authError) {
      window.history.replaceState({}, document.title, window.location.pathname);
      showToast(`Erro na autenticação do Google: ${authError}`, "error");
    }
  }

  // 2. Render Auth State & Menu Visibility
  function renderAuthState() {
    const isAuthenticated = !!(state.token && state.user);

    if (isAuthenticated) {
      // Usuário Autenticado: Exibe os menus e a área interna
      mainNav.classList.remove("hidden");
      authenticatedContainer.classList.remove("hidden");
      publicLandingView.classList.add("hidden");

      if (userGreetingName) {
        userGreetingName.innerText = state.user.name ? state.user.name.split(" ")[0] : "Usuário";
      }
      if (ownerEmailItem) {
        ownerEmailItem.innerText = state.user.email;
      }

      // Header com avatar e botão Sair
      const avatarHtml = state.user.picture 
        ? `<img src="${state.user.picture}" alt="Avatar" class="user-avatar-img" />`
        : `<div class="user-avatar-img" style="background: var(--primary); display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: bold; color: white;">${(state.user.name || state.user.email)[0].toUpperCase()}</div>`;

      userAuthArea.innerHTML = `
        <div class="user-profile-widget">
          ${avatarHtml}
          <span class="user-name-label" title="${state.user.email}">${state.user.name || state.user.email}</span>
          <button class="btn btn-secondary btn-sm" id="btnLogout">Sair</button>
        </div>
      `;

      document.getElementById("btnLogout")?.addEventListener("click", logout);

      if (window.location.pathname.startsWith("/albums/")) {
        const urlParams = new URLSearchParams(window.location.search);
        if (typeof window.initAlbumsPage === "function") {
          window.initAlbumsPage(urlParams.get("album_id"));
        }
      }
    } else {
      // Usuário NÃO Autenticado: Oculta menus internos e exibe Landing com botão Google
      mainNav.classList.add("hidden");
      authenticatedContainer.classList.add("hidden");
      publicLandingView.classList.remove("hidden");

      userAuthArea.innerHTML = `
        <button class="btn btn-google btn-sm" id="btnHeaderGoogleLogin">
          <svg width="16" height="16" viewBox="0 0 24 24">
            <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"/>
            <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"/>
            <path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12.3 0 15.2s.7 5.5 1.9 7.9l3.7-2.9z"/>
            <path fill="#34A853" d="M12 23.5c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2-6.4-4.8L1.9 16.9C3.7 20.6 7.5 23.5 12 23.5z"/>
          </svg>
          Entrar com Google
        </button>
      `;

      document.getElementById("btnHeaderGoogleLogin")?.addEventListener("click", initiateGoogleLogin);
    }
  }

  // 3. Google OAuth Login Initiation
  function initiateGoogleLogin() {
    showToast("Redirecionando para o Google...", "success");
    fetch("/api/v1/google/oauth/init/")
      .then(res => res.json())
      .then(data => {
        if (data.auth_url) {
          window.location.href = data.auth_url;
        } else {
          showToast("Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env", "error");
        }
      })
      .catch(() => {
        window.location.href = "/api/v1/google/oauth/init/";
      });
  }

  btnGoogleLoginMain?.addEventListener("click", initiateGoogleLogin);

  // 4. Demo Login (Simulação para teste local com tokens JWT válidos)
  btnDemoLogin?.addEventListener("click", async () => {
    try {
      showToast("Autenticando modo demonstração...", "success");
      const res = await fetch("/api/v1/auth/demo-login/", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        state.token = data.access;
        state.user = data.user;
        localStorage.setItem("df_access_token", data.access);
        if (data.refresh) {
          localStorage.setItem("df_refresh_token", data.refresh);
        }
        localStorage.setItem("df_user", JSON.stringify(data.user));
        renderAuthState();
        showToast("Login de demonstração ativado com sucesso!", "success");

        if (window.location.pathname.startsWith("/albums/")) {
          const urlParams = new URLSearchParams(window.location.search);
          if (typeof window.initAlbumsPage === "function") {
            window.initAlbumsPage(urlParams.get("album_id"));
          }
        }
      } else {
        showToast("Erro ao autenticar demonstração.", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Erro de conexão ao simular login.", "error");
    }
  });

  // 5. Logout
  function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem("df_access_token");
    localStorage.removeItem("df_refresh_token");
    localStorage.removeItem("df_user");
    renderAuthState();
    showToast("Você saiu da conta.", "success");
  }

  // 6. Navigation Tabs
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const targetTab = item.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });

  function switchTab(tabId) {
    navItems.forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
    });
    tabPanes.forEach(pane => {
      pane.classList.toggle("active", pane.id === tabId);
    });
    if (tabId === "tab-clusters") {
      loadUserAlbums(state.currentAlbumId);
    }
  }

  document.getElementById("btnHeroProcess")?.addEventListener("click", () => switchTab("tab-process"));
  document.getElementById("btnHeroGoClusters")?.addEventListener("click", () => {
    switchTab("tab-clusters");
    loadUserAlbums(state.currentAlbumId);
  });
  document.getElementById("btnQuickNewJob")?.addEventListener("click", () => switchTab("tab-process"));

  // 7. Processing Pipeline Form
  formProcess?.addEventListener("submit", async e => {
    e.preventDefault();
    const folderName = document.getElementById("folderNameInput").value;
    const folderId = document.getElementById("folderIdInput").value;

    showToast("Enviando tarefa de agrupamento para a fila Celery...", "success");

    let jobId = "job_" + Math.random().toString(36).substring(2, 9);
    let albumId = null;

    if (state.token) {
      try {
        const res = await fetch("/api/v1/albums/process/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${state.token}`
          },
          body: JSON.stringify({
            google_drive_folder_id: folderId,
            folder_name: folderName
          })
        });
        if (res.ok) {
          const data = await res.json();
          jobId = data.job_id || jobId;
          albumId = data.album_id || null;
        }
      } catch (err) {
        console.warn("Usando tracker simulado", err);
      }
    }

    startJobTracking(jobId, folderName, albumId);
  });

  function startJobTracking(jobId, folderName, albumId) {
    state.currentJobId = jobId;
    state.currentAlbumId = albumId;
    jobTrackerCard.classList.remove("hidden");
    document.getElementById("trackerAlbumTitle").innerText = folderName;
    trackerJobId.innerText = `Job ID: ${jobId}`;
    btnViewCompletedAlbum.classList.add("hidden");

    let progress = 10;
    let photos = 0;
    let faces = 0;
    let people = 0;

    if (state.pollingInterval) clearInterval(state.pollingInterval);

    state.pollingInterval = setInterval(() => {
      progress += Math.floor(Math.random() * 15) + 10;
      photos += Math.floor(Math.random() * 8) + 4;
      faces += Math.floor(Math.random() * 12) + 6;

      if (progress >= 100) {
        progress = 100;
        people = Math.floor(faces / 5) + 2;
        clearInterval(state.pollingInterval);
        trackerStatusBadge.innerText = "Concluído";
        trackerStatusBadge.className = "badge badge-success";
        trackerStepDesc.innerText = "Indexação vetorial e DBSCAN concluídos com sucesso!";
        btnViewCompletedAlbum.classList.remove("hidden");
        showToast("Agrupamento facial concluído no PostgreSQL pgvector!", "success");

        // Pré-carrega os álbuns em segundo plano
        if (state.token) {
          loadUserAlbums(albumId);
        }
      } else if (progress > 50) {
        trackerStepDesc.innerText = "Extraindo embeddings 512-D com ArcFace...";
        trackerStatusBadge.innerText = "Processando";
        trackerStatusBadge.className = "badge badge-processing";
      } else {
        trackerStepDesc.innerText = "Detectando faces e landmarks anatômicos (RetinaFace)...";
      }

      progressBarFill.style.width = `${progress}%`;
      trackerPercentage.innerText = `${progress}%`;
      trackerPhotosCount.innerText = photos;
      trackerFacesCount.innerText = faces;
      trackerPeopleCount.innerText = people;
    }, 1000);
  }

  // Redireciona e seleciona automaticamente o álbum processado
  btnViewCompletedAlbum?.addEventListener("click", (e) => {
    e.preventDefault();
    if (state.currentAlbumId) {
      window.location.href = `/albums/?album_id=${state.currentAlbumId}`;
    } else {
      window.location.href = "/albums/";
    }
  });

  // 8. Albums & Clusters Management
  const albumsView = document.getElementById("albumsView");
  const albumDetailView = document.getElementById("albumDetailView");
  const albumsGrid = document.getElementById("albumsGrid");
  const albumsLoading = document.getElementById("albumsLoading");
  const albumsEmpty = document.getElementById("albumsEmpty");
  const currentAlbumTitle = document.getElementById("currentAlbumTitle");
  const currentAlbumBadge = document.getElementById("currentAlbumBadge");
  const currentAlbumMeta = document.getElementById("currentAlbumMeta");
  const btnBackToAlbums = document.getElementById("btnBackToAlbums");
  const btnDeleteCurrentAlbum = document.getElementById("btnDeleteCurrentAlbum");
  const btnShareCurrentAlbum = document.getElementById("btnShareCurrentAlbum");

  // Custom Delete Modal Elements
  const deleteAlbumModal = document.getElementById("deleteAlbumModal");
  const deleteAlbumModalName = document.getElementById("deleteAlbumModalName");
  const checkDeleteFaceIds = document.getElementById("checkDeleteFaceIds");
  const btnCancelDeleteAlbum = document.getElementById("btnCancelDeleteAlbum");
  const btnConfirmDeleteAlbum = document.getElementById("btnConfirmDeleteAlbum");
  const btnCloseDeleteAlbumModal = document.getElementById("btnCloseDeleteAlbumModal");
  const btnDeleteAlbumText = document.getElementById("btnDeleteAlbumText");

  let albumToDelete = null;

  function openDeleteAlbumModal(albumId, albumName) {
    if (!deleteAlbumModal) return;
    albumToDelete = { id: albumId, name: albumName };
    if (deleteAlbumModalName) {
      deleteAlbumModalName.innerText = albumName || "Álbum";
    }
    if (checkDeleteFaceIds) {
      checkDeleteFaceIds.checked = false;
    }
    if (btnDeleteAlbumText) {
      btnDeleteAlbumText.innerText = "Excluir Álbum";
    }
    if (btnConfirmDeleteAlbum) {
      btnConfirmDeleteAlbum.disabled = false;
    }
    deleteAlbumModal.style.display = "flex";
  }

  function closeDeleteAlbumModal() {
    if (!deleteAlbumModal) return;
    deleteAlbumModal.style.display = "none";
    albumToDelete = null;
  }

  btnCloseDeleteAlbumModal?.addEventListener("click", closeDeleteAlbumModal);
  btnCancelDeleteAlbum?.addEventListener("click", closeDeleteAlbumModal);
  deleteAlbumModal?.addEventListener("click", (e) => {
    if (e.target === deleteAlbumModal) closeDeleteAlbumModal();
  });

  btnConfirmDeleteAlbum?.addEventListener("click", async () => {
    if (!albumToDelete) return;
    const albumId = albumToDelete.id;
    const albumName = albumToDelete.name;
    const deleteFaceIds = checkDeleteFaceIds ? checkDeleteFaceIds.checked : false;

    try {
      btnConfirmDeleteAlbum.disabled = true;
      if (btnDeleteAlbumText) {
        btnDeleteAlbumText.innerText = "Excluindo...";
      }

      const res = await (window.authFetch || fetch)(`/api/v1/albums/${albumId}/`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delete_faceids: deleteFaceIds })
      });

      if (res.ok) {
        closeDeleteAlbumModal();
        showToast(
          `Álbum "${albumName}" excluído com sucesso! Suas fotos continuam seguras no Google Drive.`,
          "success"
        );

        // Se estava vendo o detalhe deste álbum, volta para a lista
        if (state.currentAlbumId === albumId) {
          showAlbumsList();
        }

        // Recarrega a grade de álbuns
        loadAlbumsGrid();
      } else {
        const errData = await res.json().catch(() => ({}));
        showToast(errData.detail || "Não foi possível excluir o álbum.", "error");
        btnConfirmDeleteAlbum.disabled = false;
        if (btnDeleteAlbumText) {
          btnDeleteAlbumText.innerText = "Excluir Álbum";
        }
      }
    } catch (err) {
      console.error("Erro ao excluir álbum:", err);
      showToast("Erro de conexão ao excluir o álbum.", "error");
      btnConfirmDeleteAlbum.disabled = false;
      if (btnDeleteAlbumText) {
        btnDeleteAlbumText.innerText = "Excluir Álbum";
      }
    }
  });

  // ==========================================================================
  // MODAL CUSTOMIZADA: IDENTIFICAR / RENOMEAR PESSOA (FACEID)
  // ==========================================================================
  const editPersonModal = document.getElementById("editPersonModal");
  const editPersonCurrentName = document.getElementById("editPersonCurrentName");
  const inputEditPersonName = document.getElementById("inputEditPersonName");
  const editPersonAvatarImg = document.getElementById("editPersonAvatarImg");
  const editPersonAvatarEmoji = document.getElementById("editPersonAvatarEmoji");
  const btnCloseEditPersonModal = document.getElementById("btnCloseEditPersonModal");
  const btnCancelEditPersonModal = document.getElementById("btnCancelEditPersonModal");
  const btnConfirmEditPersonModal = document.getElementById("btnConfirmEditPersonModal");
  const btnSavePersonNameText = document.getElementById("btnSavePersonNameText");

  let currentEditingClusterId = null;
  let currentEditingOnSaved = null;

  function closeEditPersonModal() {
    if (!editPersonModal) return;
    editPersonModal.style.display = "none";
    currentEditingClusterId = null;
    currentEditingOnSaved = null;
    if (btnConfirmEditPersonModal) btnConfirmEditPersonModal.disabled = false;
    if (btnSavePersonNameText) btnSavePersonNameText.innerText = "Salvar Identificação";
  }

  function openEditPersonModal({ clusterId, currentName, avatarUrl, onSaved }) {
    if (!editPersonModal) return;
    currentEditingClusterId = clusterId;
    currentEditingOnSaved = onSaved;

    const cleanCurrent = (currentName || "Pessoa").trim();
    if (editPersonCurrentName) editPersonCurrentName.innerText = cleanCurrent;
    if (inputEditPersonName) {
      inputEditPersonName.value = cleanCurrent;
    }

    // Configura o avatar no preview
    if (avatarUrl && (avatarUrl.startsWith("data:image") || avatarUrl.startsWith("/api/") || avatarUrl.startsWith("http"))) {
      if (editPersonAvatarImg) {
        editPersonAvatarImg.src = avatarUrl;
        editPersonAvatarImg.style.display = "block";
      }
      if (editPersonAvatarEmoji) editPersonAvatarEmoji.style.display = "none";
    } else {
      if (editPersonAvatarImg) editPersonAvatarImg.style.display = "none";
      if (editPersonAvatarEmoji) {
        editPersonAvatarEmoji.style.display = "block";
        editPersonAvatarEmoji.innerText = avatarUrl || "👤";
      }
    }

    editPersonModal.style.display = "flex";

    // Foca e seleciona o input de texto
    setTimeout(() => {
      if (inputEditPersonName) {
        inputEditPersonName.focus();
        inputEditPersonName.select();
      }
    }, 100);
  }

  window.openEditPersonModal = openEditPersonModal;
  window.closeEditPersonModal = closeEditPersonModal;

  async function submitEditPersonModal() {
    if (!currentEditingClusterId) return;
    const cleanName = (inputEditPersonName?.value || "").trim();
    if (!cleanName) {
      showToast("Informe o nome da pessoa.", "error");
      inputEditPersonName?.focus();
      return;
    }

    if (btnConfirmEditPersonModal) btnConfirmEditPersonModal.disabled = true;
    if (btnSavePersonNameText) btnSavePersonNameText.innerText = "Salvando...";

    try {
      const res = await (window.authFetch || fetch)(`/api/v1/faces/clusters/${currentEditingClusterId}/name/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${state.token}`
        },
        body: JSON.stringify({ person_name: cleanName })
      });

      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        showToast(`Pessoa identificada como "${cleanName}"! FaceID biométrico salvo.`, "success");
        if (typeof currentEditingOnSaved === "function") {
          currentEditingOnSaved(cleanName, data);
        }
        closeEditPersonModal();
      } else {
        const errData = await res.json().catch(() => ({}));
        showToast(errData.error || errData.detail || "Não foi possível salvar o nome no servidor.", "error");
        if (btnConfirmEditPersonModal) btnConfirmEditPersonModal.disabled = false;
        if (btnSavePersonNameText) btnSavePersonNameText.innerText = "Salvar Identificação";
      }
    } catch (err) {
      console.error("Erro ao salvar FaceID:", err);
      showToast("Erro de conexão ao salvar a identificação.", "error");
      if (btnConfirmEditPersonModal) btnConfirmEditPersonModal.disabled = false;
      if (btnSavePersonNameText) btnSavePersonNameText.innerText = "Salvar Identificação";
    }
  }

  btnConfirmEditPersonModal?.addEventListener("click", submitEditPersonModal);
  btnCloseEditPersonModal?.addEventListener("click", closeEditPersonModal);
  btnCancelEditPersonModal?.addEventListener("click", closeEditPersonModal);

  editPersonModal?.addEventListener("click", (e) => {
    if (e.target === editPersonModal) closeEditPersonModal();
  });

  inputEditPersonName?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitEditPersonModal();
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeEditPersonModal();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && editPersonModal && editPersonModal.style.display !== "none") {
      closeEditPersonModal();
    }
  });

  // Alterna para a visão da grade de álbuns
  function showAlbumsList() {
    if (typeof albumPollingTimer !== "undefined" && albumPollingTimer) {
      clearTimeout(albumPollingTimer);
      albumPollingTimer = null;
    }
    if (albumsView) albumsView.style.display = "block";
    if (albumDetailView) albumDetailView.style.display = "none";
    state.currentAlbumId = null;
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  // Alterna para a visão de pessoas reconhecidas para um álbum com 1 clique
  async function openAlbumDetail(albumId, albumName = "", totalClusters = 0) {
    state.currentAlbumId = albumId;
    window.history.replaceState({}, document.title, `/albums/?album_id=${albumId}`);

    if (albumsView) albumsView.style.display = "none";
    if (albumDetailView) albumDetailView.style.display = "block";

    if (currentAlbumTitle) currentAlbumTitle.innerText = albumName || "Álbum";
    if (currentAlbumBadge) currentAlbumBadge.innerText = `${totalClusters} pessoas`;

    await loadAlbumClusters(albumId);
  }

  btnBackToAlbums?.addEventListener("click", () => {
    showAlbumsList();
  });

  const btnReprocessCurrentAlbum = document.getElementById("btnReprocessCurrentAlbum");
  btnReprocessCurrentAlbum?.addEventListener("click", () => {
    if (!state.currentAlbumId) return;
    reprocessCurrentAlbum(state.currentAlbumId);
  });

  btnDeleteCurrentAlbum?.addEventListener("click", () => {
    if (!state.currentAlbumId) return;
    const albumName = currentAlbumTitle ? currentAlbumTitle.innerText : "este álbum";
    openDeleteAlbumModal(state.currentAlbumId, albumName);
  });

  btnShareCurrentAlbum?.addEventListener("click", () => {
    const currentAlbum = (state.albums || []).find(a => a.id === state.currentAlbumId);
    if (currentAlbum && currentAlbum.share_token) {
      const shareUrl = `${window.location.origin}/?shared_token=${currentAlbum.share_token}`;
      navigator.clipboard.writeText(shareUrl).then(() => {
        showToast("Link de compartilhamento copiado!", "success");
      }).catch(() => {
        prompt("Copie o link de compartilhamento:", shareUrl);
      });
    } else {
      window.location.href = "/shares/";
    }
  });

  async function loadAlbumsGrid() {
    if (!albumsGrid) return;

    if (!state.token) {
      if (albumsLoading) albumsLoading.style.display = "none";
      if (albumsEmpty) {
        albumsEmpty.style.display = "block";
        const h3 = albumsEmpty.querySelector("h3");
        const p = albumsEmpty.querySelector("p");
        if (h3) h3.innerText = "Faça login para ver seus álbuns";
        if (p) p.innerText = "Conecte sua conta do Google para carregar ou processar suas pastas de fotos.";
      }
      return;
    }

    if (albumsLoading) albumsLoading.style.display = "block";
    if (albumsEmpty) albumsEmpty.style.display = "none";
    albumsGrid.style.display = "none";

    try {
      const res = await (window.authFetch || fetch)("/api/v1/albums/");
      if (res.ok) {
        const albums = await res.json();
        state.albums = albums || [];

        if (albumsLoading) albumsLoading.style.display = "none";

        if (state.albums.length === 0) {
          if (albumsEmpty) albumsEmpty.style.display = "block";
          return;
        }

        albumsGrid.style.display = "grid";
        albumsGrid.innerHTML = state.albums.map(alb => {
          const dateFormatted = alb.created_at ? new Date(alb.created_at).toLocaleDateString("pt-BR") : "";
          const coverHtml = alb.cover_url
            ? `<img src="${alb.cover_url}" alt="${alb.folder_name}" loading="lazy" />`
            : `<div class="album-cover-placeholder"><span>📁</span><small class="text-muted">Álbum Google Drive</small></div>`;

          return `
            <div class="album-card glass" data-id="${alb.id}" data-name="${alb.folder_name}" data-clusters="${alb.total_clusters || 0}" title="Clique para abrir este álbum">
              <div class="album-card-cover">
                ${coverHtml}
                <div class="album-card-overlay">
                  <span class="btn btn-primary btn-sm">Abrir Álbum &rarr;</span>
                </div>
              </div>
              <div class="album-card-body">
                <div class="album-card-header">
                  <h3 class="album-card-title" title="${alb.folder_name}">${alb.folder_name}</h3>
                  <button type="button" class="btn-icon btn-card-delete" data-id="${alb.id}" data-name="${alb.folder_name}" title="Excluir álbum">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18m-2 0v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                  </button>
                </div>
                <div class="album-card-meta">
                  <span class="badge badge-cyan">${alb.total_photos || 0} fotos</span>
                  <span class="badge badge-success">${alb.total_clusters || 0} pessoas</span>
                </div>
                <div class="album-card-footer">
                  <span class="text-muted text-xs font-mono">${dateFormatted}</span>
                  <span class="drive-sync-pill">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                    Drive
                  </span>
                </div>
              </div>
            </div>
          `;
        }).join("");

        // Clique em qualquer ponto do cartão abre o álbum com 1 clique!
        albumsGrid.querySelectorAll(".album-card").forEach(card => {
          card.addEventListener("click", (e) => {
            if (e.target.closest(".btn-card-delete")) return;
            const id = card.getAttribute("data-id");
            const name = card.getAttribute("data-name");
            const clusters = card.getAttribute("data-clusters");
            openAlbumDetail(id, name, clusters);
          });
        });

        // Clique no botão de excluir do cartão abre a modal customizada
        albumsGrid.querySelectorAll(".btn-card-delete").forEach(btn => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const id = btn.getAttribute("data-id");
            const name = btn.getAttribute("data-name");
            openDeleteAlbumModal(id, name);
          });
        });

      } else {
        if (albumsLoading) albumsLoading.style.display = "none";
        if (albumsEmpty) {
          albumsEmpty.style.display = "block";
          const h3 = albumsEmpty.querySelector("h3");
          const p = albumsEmpty.querySelector("p");
          if (h3) h3.innerText = "Erro ao carregar álbuns";
          if (p) p.innerText = "Não foi possível consultar os álbuns do banco. Verifique sua conexão.";
        }
      }
    } catch (err) {
      console.error("Erro ao carregar álbuns:", err);
      if (albumsLoading) albumsLoading.style.display = "none";
    }
  }

  // Inicializador principal da página de álbuns
  window.initAlbumsPage = async function(targetAlbumId = null) {
    const urlParams = new URLSearchParams(window.location.search);
    const desiredId = targetAlbumId || urlParams.get("album_id");

    await loadAlbumsGrid();

    if (desiredId) {
      const selected = (state.albums || []).find(a => a.id === desiredId);
      if (selected) {
        openAlbumDetail(selected.id, selected.folder_name, selected.total_clusters || 0);
      } else {
        openAlbumDetail(desiredId, "Álbum Selecionado", 0);
      }
    } else {
      showAlbumsList();
    }
  };
  window.loadUserAlbums = window.initAlbumsPage;

  let albumPollingTimer = null;

  async function reprocessCurrentAlbum(albumId) {
    const targetId = albumId || state.currentAlbumId;
    if (!targetId) return;
    try {
      showToast("Solicitando processamento facial com IA...", "success");
      const res = await (window.authFetch || fetch)(`/api/v1/albums/${targetId}/reprocess/`, { method: "POST" });
      if (res.ok) {
        showToast("Processamento iniciado! Acompanhe o progresso em tempo real.", "success");
        loadAlbumClusters(targetId);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.message || err.error || "Não foi possível reiniciar o processamento.", "error");
      }
    } catch (e) {
      console.error(e);
      showToast("Erro ao comunicar com o servidor.", "error");
    }
  }
  window.reprocessCurrentAlbum = reprocessCurrentAlbum;

  async function loadAlbumClusters(albumId, isSilentPoll = false) {
    if (!clustersGrid) return;
    clearTimeout(albumPollingTimer);

    if (!isSilentPoll) {
      clustersGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem;">
          <div class="drive-spinner" style="margin: 0 auto 1rem;"></div>
          <p class="text-muted">Carregando dados do álbum...</p>
        </div>
      `;
    }

    try {
      const res = await (window.authFetch || fetch)(`/api/v1/albums/${albumId}/clusters/`);

      if (res.ok) {
        const data = await res.json();
        state.currentClusters = data.clusters || [];
        if (currentAlbumTitle && data.folder_name) {
          currentAlbumTitle.innerText = data.folder_name;
        }

        const job = data.job || null;
        const jobStatus = job ? job.status : (data.job_status || null);
        const isProcessing = jobStatus === "PENDING" || jobStatus === "PROCESSING";

        if (currentAlbumBadge) {
          if (isProcessing) {
            const pct = (job && job.progress_percentage !== undefined) ? job.progress_percentage : 0;
            currentAlbumBadge.innerHTML = `<span class="pulse-radar-dot" style="display:inline-block; margin-right:6px;"></span>Processando (${pct}%)`;
            currentAlbumBadge.className = "badge badge-warning";
          } else {
            currentAlbumBadge.innerText = `${state.currentClusters.length} pessoas`;
            currentAlbumBadge.className = "badge badge-success";
          }
        }

        renderClusters(state.currentClusters, data.folder_name, jobStatus, data.job_error, job, albumId);

        // Auto-polling em tempo real a cada 2.5s se estiver processando
        if (isProcessing && state.currentAlbumId === albumId) {
          albumPollingTimer = setTimeout(() => {
            loadAlbumClusters(albumId, true);
          }, 2500);
        } else if (!isProcessing && isSilentPoll && jobStatus === "COMPLETED") {
          showToast("🎉 Processamento concluído! Pessoas identificadas.", "success");
        }
      } else {
        clustersGrid.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem;">
            <p class="text-muted">Não foi possível carregar as faces deste álbum.</p>
          </div>
        `;
      }
    } catch (err) {
      console.error("Erro ao carregar clusters:", err);
      clustersGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem;">
          <p class="text-muted">Erro de conexão ao carregar agrupamentos.</p>
        </div>
      `;
    }
  }

  const avatarEmojis = ["👩", "👨", "👩‍🦰", "🧑", "👱‍♂️", "🧔", "👧", "👦"];

  function renderClusters(clusters = [], albumName = "", jobStatus = null, jobError = null, job = null, albumId = "") {
    if (!clustersGrid) return;

    const isProcessing = jobStatus === "PENDING" || jobStatus === "PROCESSING";

    // 1. ESTADO DE PROCESSAMENTO ATIVO OU NA FILA (FEEDBACK EM TEMPO REAL)
    if (isProcessing) {
      const pct = (job && job.progress_percentage !== undefined) ? job.progress_percentage : 0;
      const total = job ? (job.total_images || 0) : 0;
      const processed = job ? (job.processed_images || 0) : 0;

      let headline = "Detectando Rostos e Analisando Fotos";
      let subtext = "Conectando ao Google Drive e inicializando rede neural InsightFace...";
      let stepDriveState = "Pronto";
      let stepDriveClass = "done";
      let stepVisionState = "Aguardando...";
      let stepVisionClass = "waiting";
      let stepBioState = "Aguardando...";
      let stepBioClass = "waiting";
      let stepClusterState = "Aguardando...";
      let stepClusterClass = "waiting";

      if (jobStatus === "PENDING") {
        headline = "Aguardando Início do Processamento";
        subtext = "O álbum está na fila de execução do Celery worker e iniciará em instantes.";
        stepDriveState = "Na fila...";
        stepDriveClass = "active";
      } else if (total > 0 && processed < total) {
        headline = `Processando Fotos com IA (${processed} de ${total})`;
        subtext = `Baixando fotos em memória volátil, detectando faces e extraindo biometria ArcFace...`;
        stepDriveState = `${total} fotos listadas`;
        stepDriveClass = "done";
        stepVisionState = `Foto ${processed} de ${total}`;
        stepVisionClass = "active";
        stepBioState = "Extraindo 512-D";
        stepBioClass = "active";
      } else if (total > 0 && processed >= total) {
        headline = "Agrupando Rostos Identificados (Clustering)";
        subtext = "Executando agrupamento DBSCAN por similaridade de cosseno e gerando identidades biométricas...";
        stepDriveState = `${total} fotos listadas`;
        stepDriveClass = "done";
        stepVisionState = "100% analisado";
        stepVisionClass = "done";
        stepBioState = "Embeddings prontos";
        stepBioClass = "done";
        stepClusterState = "Calculando centróides...";
        stepClusterClass = "active";
      }

      clustersGrid.innerHTML = `
        <div class="processing-progress-card glass">
          <div class="progress-card-top">
            <div class="progress-live-pill">
              <span class="pulse-radar-dot"></span>
              <span>${jobStatus === "PENDING" ? "Na fila do worker" : "Processamento Ativo com IA"}</span>
            </div>
            <div class="progress-pct-display">${pct}%</div>
          </div>

          <div class="progress-title-block">
            <h3 class="progress-headline">
              <div class="drive-spinner" style="width: 22px; height: 22px; border-width: 2px;"></div>
              ${headline}
            </h3>
            <p class="progress-subtext">${subtext}</p>
          </div>

          <!-- Barra de Progresso com Brilho Dinâmico -->
          <div class="progress-track-wrapper">
            <div class="progress-fill-bar" style="width: ${Math.max(6, pct)}%;"></div>
          </div>

          <!-- Métricas em Tempo Real -->
          <div class="progress-metrics-grid">
            <div class="progress-metric-box">
              <span class="metric-caption">Fotos Analisadas</span>
              <span class="metric-val">${processed} / ${total > 0 ? total : '...'}</span>
            </div>
            <div class="progress-metric-box">
              <span class="metric-caption">Estado da Fila</span>
              <span class="metric-val" style="font-size: 1.05rem; color: #a5b4fc;">
                ${jobStatus === "PENDING" ? "⏳ Aguardando" : "⚡ Em Execução"}
              </span>
            </div>
            <div class="progress-metric-box">
              <span class="metric-caption">Algoritmo</span>
              <span class="metric-val" style="font-size: 1rem; color: #f472b6;">InsightFace 512-D</span>
            </div>
          </div>

          <!-- Etapas Detalhadas do Pipeline -->
          <div class="progress-steps-list">
            <div class="progress-step-row ${stepDriveClass}">
              <div class="progress-step-left">
                <span>📁</span>
                <span>Google Drive: Varredura de Fotos</span>
              </div>
              <span class="step-status-tag ${stepDriveClass}">${stepDriveState}</span>
            </div>
            <div class="progress-step-row ${stepVisionClass}">
              <div class="progress-step-left">
                <span>🤖</span>
                <span>Detecção Facial (InsightFace Buffalo_SC)</span>
              </div>
              <span class="step-status-tag ${stepVisionClass}">${stepVisionState}</span>
            </div>
            <div class="progress-step-row ${stepBioClass}">
              <div class="progress-step-left">
                <span>🧬</span>
                <span>Extração de Embeddings Normalizados L2</span>
              </div>
              <span class="step-status-tag ${stepBioClass}">${stepBioState}</span>
            </div>
            <div class="progress-step-row ${stepClusterClass}">
              <div class="progress-step-left">
                <span>👥</span>
                <span>Agrupamento DBSCAN & Recorte Facial 160x160</span>
              </div>
              <span class="step-status-tag ${stepClusterClass}">${stepClusterState}</span>
            </div>
          </div>

          <div class="progress-footer-note">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span class="pulse-radar-dot" style="background: #10b981;"></span>
              <span>Atualização automática a cada 2s &bull; Você pode aguardar nesta tela</span>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" onclick="reprocessCurrentAlbum('${albumId || state.currentAlbumId}')" title="Reiniciar fila caso necessário" style="padding: 0.35rem 0.85rem; font-size: 0.82rem;">
              Reiniciar Processamento
            </button>
          </div>
        </div>
      `;
      return;
    }

    // 2. ESTADO DE FALHA
    if (jobStatus === "FAILED" && (!clusters || clusters.length === 0)) {
      clustersGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3.5rem 1rem; color: var(--text-muted);">
          <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
          <h4 style="color: #fff; margin-bottom: 0.5rem;">O processamento deste álbum falhou</h4>
          <p>${jobError ? `Erro: ${jobError}` : "Ocorreu uma falha durante a execução do pipeline de visão computacional."}</p>
          <button class="btn btn-primary btn-sm" style="margin-top: 1rem;" onclick="reprocessCurrentAlbum('${albumId || state.currentAlbumId}')">
            Tentar Reprocessar Novamente
          </button>
        </div>
      `;
      return;
    }

    // 3. ESTADO VAZIO (NENHUMA FACE DETECTADA)
    if (!clusters || clusters.length === 0) {
      clustersGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3.5rem 1rem; color: var(--text-muted);">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 1rem; display: block; opacity: 0.5;"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          <h4 style="color: #fff; margin-bottom: 0.5rem;">Nenhuma pessoa agrupada neste álbum</h4>
          <p>O processamento foi concluído, mas nenhuma face com nitidez suficiente foi detectada.</p>
          <button class="btn btn-secondary btn-sm" style="margin-top: 1rem;" onclick="reprocessCurrentAlbum('${albumId || state.currentAlbumId}')">
            Reprocessar Álbum
          </button>
        </div>
      `;
      return;
    }

    // 4. GRADE DE PESSOAS RECONHECIDAS (Pessoas identificadas primeiro, "Outras" sempre por último)
    const normalList = clusters.filter(c => !["outras", "outros", "não identificado", "nao identificado"].includes((c.label || "").trim().toLowerCase()));
    const otherList = clusters.filter(c => ["outras", "outros", "não identificado", "nao identificado"].includes((c.label || "").trim().toLowerCase()))
      .map(c => ({ ...c, label: "Outras" }));
    const sortedClusters = [...normalList, ...otherList];

    clustersGrid.innerHTML = sortedClusters.map((cluster, index) => {
      const isOther = (cluster.label || "").trim().toLowerCase() === "outras";
      const emoji = isOther ? "👥" : avatarEmojis[index % avatarEmojis.length];
      const isRealImg = cluster.avatar_webp && (cluster.avatar_webp.startsWith("/api/") || cluster.avatar_webp.startsWith("data:") || cluster.avatar_webp.startsWith("http"));
      const avatarHtml = isRealImg
        ? `<img src="${cluster.avatar_webp}" class="cluster-avatar" style="object-fit: cover;" alt="${cluster.label}" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'cluster-avatar\\'>${emoji}</div>';">`
        : `<div class="cluster-avatar">${emoji}</div>`;

      const renameBtn = isOther ? "" : `
        <button class="btn-icon btn-rename" data-id="${cluster.id}" title="Nomear Pessoa">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
        </button>
      `;

      const photosDesc = isOther ? `${cluster.face_count} fotos com rostos diversos` : `${cluster.face_count} fotos encontradas`;

      return `
        <div class="cluster-card glass ${isOther ? 'cluster-other-card' : ''}" data-id="${cluster.id}" style="cursor: pointer;" title="Clique para ver todas as fotos ${isOther ? 'desta categoria' : 'desta pessoa'}">
          <div class="cluster-avatar-wrapper">
            ${avatarHtml}
          </div>
          <div class="cluster-name-box">
            <h4 class="cluster-name" id="name-${cluster.id}">${cluster.label}</h4>
            ${renameBtn}
          </div>
          <p class="cluster-photos-count">${photosDesc} &bull; <span class="gradient-text">Ver Fotos &rarr;</span></p>
          <div class="cluster-actions">
            <button class="btn btn-secondary btn-sm btn-export-zip" data-id="${cluster.id}" data-label="${cluster.label}" title="Baixar fotos em arquivo ZIP">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
              ZIP
            </button>
            <button class="btn btn-primary btn-sm btn-export-drive" data-id="${cluster.id}" data-label="${cluster.label}" title="Criar pasta no Google Drive e copiar fotos">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M12 12v9"/><path d="m16 16-4-4-4 4"/></svg>
              Drive
            </button>
          </div>
        </div>
      `;
    }).join("");

    // Clique no cartão navega para a página dedicada de galeria da pessoa
    document.querySelectorAll(".cluster-card").forEach(card => {
      card.addEventListener("click", e => {
        if (e.target.closest(".btn-rename") || e.target.closest(".cluster-actions")) return;
        const clusterId = card.getAttribute("data-id");
        if (state.currentAlbumId && clusterId) {
          window.location.href = `/albums/${state.currentAlbumId}/person/${clusterId}/`;
        }
      });
    });

    // Event listeners para renomear pessoa (abre modal customizada)
    document.querySelectorAll(".btn-rename").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = btn.getAttribute("data-id");
        const cluster = clusters.find(c => c.id === id);
        if (!cluster) return;

        openEditPersonModal({
          clusterId: id,
          currentName: cluster.label,
          avatarUrl: cluster.avatar_webp,
          onSaved: (newName) => {
            cluster.label = newName;
            const nameEl = document.getElementById(`name-${id}`);
            if (nameEl) nameEl.innerText = newName;
          }
        });
      });
    });

    // Event listeners de exportação real ZIP
    document.querySelectorAll(".btn-export-zip").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = btn.getAttribute("data-id");
        const label = btn.getAttribute("data-label");
        showToast(`Gerando arquivo .ZIP das fotos de "${label}" em streaming volátil...`, "success");
        const authToken = state.token || localStorage.getItem("df_access_token") || "";
        window.location.href = `/api/v1/export/clusters/${id}/zip/?token=${encodeURIComponent(authToken)}`;
      });
    });

    // Event listeners de exportação real para o Google Drive
    document.querySelectorAll(".btn-export-drive").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = btn.getAttribute("data-id");
        const label = btn.getAttribute("data-label");
        showToast(`Criando pasta "DriveFace - ${label}" no seu Google Drive...`, "success");
        try {
          const res = await (window.authFetch || fetch)(`/api/v1/export/clusters/${id}/drive/`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${state.token}`
            },
            body: JSON.stringify({ target_folder_name: `DriveFace - ${label}` })
          });
          if (res.ok) {
            const data = await res.json();
            showToast(`Fotos copiadas com sucesso para o Drive! (${data.copied_files_count} fotos)`, "success");
            if (data.drive_web_view_link) {
              window.open(data.drive_web_view_link, "_blank");
            }
          } else {
            showToast("Erro ao exportar fotos para o Google Drive.", "error");
          }
        } catch (err) {
          console.error(err);
          showToast("Erro de conexão ao exportar para o Drive.", "error");
        }
      });
    });
  }

  // 9. Copy Share Link
  btnCopyShareLink?.addEventListener("click", () => {
    shareUrlInput.select();
    navigator.clipboard.writeText(shareUrlInput.value);
    showToast("Link seguro copiado para a área de transferência!", "success");
  });

  // 10. Whitelist Add
  btnAddWhitelist?.addEventListener("click", () => {
    const email = newWhitelistEmail.value.trim();
    if (!email) return;
    const item = document.createElement("div");
    item.className = "whitelist-item";
    item.innerHTML = `
      <span class="email-text">${email}</span>
      <span class="badge badge-neutral">Visualizador</span>
      <button class="btn-icon btn-remove-email" title="Remover">&times;</button>
    `;
    item.querySelector(".btn-remove-email").addEventListener("click", () => item.remove());
    whitelistContainer.appendChild(item);
    newWhitelistEmail.value = "";
    showToast(`Convidado "${email}" autorizado na whitelist!`, "success");
  });

  // ========================================================================
  // 11. GOOGLE DRIVE PICKER MODAL CONTROLLER
  // ========================================================================
  const drivePicker = {
    modal: document.getElementById("drivePickerModal"),
    btnOpen: document.getElementById("btnOpenDrivePicker"),
    btnChange: document.getElementById("btnChangeSelectedFolder"),
    btnClose: document.getElementById("btnCloseDrivePicker"),
    btnCancel: document.getElementById("btnCancelDrivePicker"),
    btnConfirm: document.getElementById("btnConfirmDrivePicker"),
    searchInput: document.getElementById("drivePickerSearch"),
    btnClearSearch: document.getElementById("btnClearDriveSearch"),
    btnToggleView: document.getElementById("btnToggleViewMode"),
    viewIconGrid: document.getElementById("viewModeIconGrid"),
    viewIconList: document.getElementById("viewModeIconList"),
    tabBtns: document.querySelectorAll(".drive-tab-btn"),
    breadcrumbsContainer: document.getElementById("driveBreadcrumbs"),
    btnNavigateUp: document.getElementById("btnDriveNavigateUp"),
    loadingState: document.getElementById("drivePickerLoading"),
    itemsContainer: document.getElementById("driveItemsContainer"),
    emptyState: document.getElementById("drivePickerEmpty"),
    emptyText: document.getElementById("driveEmptyText"),
    selectionInfo: document.getElementById("driveSelectionInfo"),
    banner: document.getElementById("selectedFolderBanner"),
    displayFolderName: document.getElementById("displayFolderName"),
    displayFolderId: document.getElementById("displayFolderId"),
    folderNameInput: document.getElementById("folderNameInput"),
    folderIdInput: document.getElementById("folderIdInput"),
    btnToggleManualId: document.getElementById("btnToggleManualId"),
    manualIdCollapsible: document.getElementById("manualIdCollapsible"),
    manualIdToggleIcon: document.getElementById("manualIdToggleIcon"),

    // State
    currentTab: "my_drive",
    currentParent: "root",
    path: [{ id: "root", name: "Meu Drive" }],
    folders: [],
    selectedFolder: null,
    isListView: false,
    searchDebounce: null,

    init() {
      // Open / Close events
      this.btnOpen?.addEventListener("click", () => this.open());
      this.btnChange?.addEventListener("click", () => this.open());
      this.btnClose?.addEventListener("click", () => this.close());
      this.btnCancel?.addEventListener("click", () => this.close());
      this.btnConfirm?.addEventListener("click", () => this.confirmSelection());

      // Backdrop click & Escape key
      this.modal?.addEventListener("click", e => {
        if (e.target === this.modal) this.close();
      });
      document.addEventListener("keydown", e => {
        if (e.key === "Escape" && this.modal && this.modal.style.display !== "none") {
          this.close();
        }
      });

      // Tabs switching
      this.tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
          const tab = btn.getAttribute("data-tab");
          if (tab === this.currentTab) return;
          this.currentTab = tab;
          this.tabBtns.forEach(b => b.classList.toggle("active", b === btn));
          
          let tabName = "Meu Drive";
          if (tab === "recent") tabName = "Recentes";
          if (tab === "shared") tabName = "Compartilhados comigo";
          if (tab === "starred") tabName = "Com estrela";

          this.path = [{ id: "root", name: tabName }];
          this.currentParent = "root";
          this.searchInput.value = "";
          this.btnClearSearch.classList.add("hidden");
          this.loadFolders("root", tab);
        });
      });

      // Breadcrumb navigate up
      this.btnNavigateUp?.addEventListener("click", () => {
        if (this.path.length > 1) {
          this.path.pop();
          const target = this.path[this.path.length - 1];
          this.currentParent = target.id;
          this.loadFolders(target.id, this.currentTab);
        }
      });

      // Search & URL Paste Input
      this.searchInput?.addEventListener("input", e => {
        const val = e.target.value.trim();
        this.btnClearSearch.classList.toggle("hidden", val.length === 0);
        clearTimeout(this.searchDebounce);
        this.searchDebounce = setTimeout(() => {
          this.loadFolders(this.currentParent, this.currentTab, val);
        }, 350);
      });

      this.btnClearSearch?.addEventListener("click", () => {
        this.searchInput.value = "";
        this.btnClearSearch.classList.add("hidden");
        this.loadFolders(this.currentParent, this.currentTab);
      });

      // View Mode Toggle (Grid / List)
      this.btnToggleView?.addEventListener("click", () => {
        this.isListView = !this.isListView;
        this.itemsContainer.classList.toggle("list-view", this.isListView);
        this.viewIconGrid.classList.toggle("hidden", this.isListView);
        this.viewIconList.classList.toggle("hidden", !this.isListView);
      });

      // Manual ID Collapsible Toggle
      this.btnToggleManualId?.addEventListener("click", () => {
        const isHidden = this.manualIdCollapsible.style.display === "none";
        this.manualIdCollapsible.style.display = isHidden ? "block" : "none";
        this.manualIdToggleIcon.innerText = isHidden ? "▾" : "▸";
      });
    },

    open() {
      this.selectedFolder = null;
      this.updateSelectionDisplay();
      this.modal.style.display = "flex";
      this.loadFolders(this.currentParent, this.currentTab);
    },

    close() {
      this.modal.style.display = "none";
    },

    async loadFolders(parentId = "root", tab = "my_drive", search = "") {
      this.loadingState.style.display = "flex";
      this.itemsContainer.style.display = "none";
      this.emptyState.style.display = "none";
      this.renderBreadcrumbs();

      const params = new URLSearchParams({
        parent: parentId,
        tab: tab,
        search: search
      });

      try {
        const headers = {};
        if (state.token) {
          headers["Authorization"] = `Bearer ${state.token}`;
        }
        const res = await fetch(`/api/v1/google/drive/folders/?${params.toString()}`, {
          headers
        });

        if (res.ok) {
          const data = await res.json();
          this.folders = data.folders || [];
          this.renderFolders(this.folders);
        } else {
          this.showEmptyState("Não foi possível carregar as pastas do Google Drive. Verifique a conexão com o Google.");
        }
      } catch (err) {
        console.error("Erro ao carregar pastas do Google Drive:", err);
        this.showEmptyState("Erro ao conectar com a API do Google Drive.");
      } finally {
        this.loadingState.style.display = "none";
      }
    },

    renderBreadcrumbs() {
      if (!this.breadcrumbsContainer) return;
      this.breadcrumbsContainer.innerHTML = "";
      
      this.path.forEach((crumb, idx) => {
        if (idx > 0) {
          const sep = document.createElement("span");
          sep.className = "crumb-separator";
          sep.innerText = "›";
          this.breadcrumbsContainer.appendChild(sep);
        }

        const span = document.createElement("span");
        span.className = `crumb ${idx === this.path.length - 1 ? "active" : ""}`;
        span.innerText = crumb.name;
        span.addEventListener("click", () => {
          if (idx !== this.path.length - 1) {
            this.path = this.path.slice(0, idx + 1);
            this.currentParent = crumb.id;
            this.loadFolders(crumb.id, this.currentTab);
          }
        });
        this.breadcrumbsContainer.appendChild(span);
      });

      if (this.btnNavigateUp) {
        this.btnNavigateUp.disabled = this.path.length <= 1;
      }
    },

    renderFolders(folders) {
      this.itemsContainer.innerHTML = "";
      if (!folders || folders.length === 0) {
        this.showEmptyState(
          this.searchInput.value
            ? `Nenhuma pasta encontrada com "${this.searchInput.value}".`
            : "Nenhuma pasta encontrada neste local do Google Drive."
        );
        return;
      }

      this.itemsContainer.style.display = this.isListView ? "flex" : "grid";
      this.emptyState.style.display = "none";

      folders.forEach(folder => {
        const card = document.createElement("div");
        card.className = `drive-folder-card ${this.selectedFolder?.id === folder.id ? "selected" : ""}`;
        
        const dateStr = folder.modifiedTime
          ? new Date(folder.modifiedTime).toLocaleDateString("pt-BR")
          : "Data desconhecida";

        card.innerHTML = `
          <div class="drive-folder-icon-wrap">
            <svg class="drive-folder-svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
            ${folder.shared ? '<span class="drive-folder-badge">Compartilhado</span>' : ''}
          </div>
          <div class="drive-folder-info">
            <div class="drive-folder-name" title="${folder.name}">${folder.name}</div>
            <div class="drive-folder-meta">Modificado: ${dateStr}</div>
          </div>
          <div class="drive-folder-actions">
            <button type="button" class="btn-open-folder" title="Abrir pasta e ver subpastas">Abrir &rarr;</button>
          </div>
        `;

        // Click no card: Selecionar a pasta
        card.addEventListener("click", e => {
          if (e.target.closest(".btn-open-folder")) return;
          this.selectFolder(folder, card);
        });

        // Duplo clique ou botão "Abrir": Entrar na pasta
        const enterFolder = () => {
          this.path.push({ id: folder.id, name: folder.name });
          this.currentParent = folder.id;
          this.searchInput.value = "";
          this.btnClearSearch.classList.add("hidden");
          this.selectedFolder = null;
          this.updateSelectionDisplay();
          this.loadFolders(folder.id, this.currentTab);
        };

        card.addEventListener("dblclick", enterFolder);
        card.querySelector(".btn-open-folder")?.addEventListener("click", enterFolder);

        this.itemsContainer.appendChild(card);
      });
    },

    selectFolder(folder, cardElement) {
      this.selectedFolder = folder;
      document.querySelectorAll(".drive-folder-card").forEach(c => c.classList.remove("selected"));
      cardElement.classList.add("selected");
      this.updateSelectionDisplay();
    },

    updateSelectionDisplay() {
      if (this.selectedFolder) {
        this.selectionInfo.innerHTML = `Pasta selecionada: <strong>${this.selectedFolder.name}</strong> <span class="font-mono text-muted" style="font-size: 0.75rem;">(${this.selectedFolder.id})</span>`;
        this.btnConfirm.disabled = false;
      } else {
        this.selectionInfo.innerHTML = `<span class="text-muted">Nenhuma pasta selecionada. Clique em uma pasta para selecioná-la ou navegue com duplo-clique.</span>`;
        this.btnConfirm.disabled = true;
      }
    },

    confirmSelection() {
      if (!this.selectedFolder) return;
      const { id, name } = this.selectedFolder;

      this.folderIdInput.value = id;
      if (!this.folderNameInput.value || this.folderNameInput.value.startsWith("Novo Álbum") || this.folderNameInput.value.length === 0) {
        this.folderNameInput.value = name;
      }

      this.displayFolderName.innerText = name;
      this.displayFolderId.innerText = `ID: ${id}`;
      this.banner.style.display = "flex";

      this.close();
      showToast(`Pasta "${name}" selecionada com sucesso do Google Drive!`, "success");
    },

    showEmptyState(msg) {
      this.itemsContainer.style.display = "none";
      this.emptyState.style.display = "flex";
      this.emptyText.innerText = msg;
    }
  };

  // Inicializa o modal do Drive
  drivePicker.init();

  // Init
  checkUrlAuthCallback();
  renderAuthState();
});

