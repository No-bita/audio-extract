(() => {
  // Application State
  const state = {
    screen: "INPUT", // INPUT | CONFIGURE | PROCESSING | COMPLETE
    source: null,
    operation: "full",
    start: "00:00",
    end: "",
    job: null,
    error: null,
    pollInterval: null,
    ytPlayer: null,
    ytApiLoading: false,
    ytApiReady: false,
    ytPlayerLoading: false,
    ytPlayerReady: false,
  };

  // DOM Elements
  const views = {
    input: document.getElementById("view-input"),
    configure: document.getElementById("view-configure"),
    processing: document.getElementById("view-processing"),
    complete: document.getElementById("view-complete"),
  };

  // Error Banner Elements
  const errorBanner = document.getElementById("error-banner");
  const errorTitle = document.getElementById("error-title");
  const errorMessage = document.getElementById("error-message");
  const btnDismissError = document.getElementById("btn-dismiss-error");

  // Input View Elements
  const inspectForm = document.getElementById("inspect-form");
  const urlInput = document.getElementById("url-input");
  const btnInspect = document.getElementById("btn-inspect");
  const btnInspectText = btnInspect.querySelector(".btn-text");
  const btnInspectLoader = btnInspect.querySelector(".btn-loader");

  // Configure View Elements
  const mediaThumb = document.getElementById("media-thumb");
  const mediaTitle = document.getElementById("media-title");
  const mediaChannel = document.getElementById("media-channel");
  const mediaDuration = document.getElementById("media-duration");
  const btnBackInput = document.getElementById("btn-back-input");

  const cardOptFull = document.getElementById("card-opt-full");
  const cardOptClip = document.getElementById("card-opt-clip");
  const optFull = document.getElementById("opt-full");
  const optClip = document.getElementById("opt-clip");

  const clipConfigPanel = document.getElementById("clip-config-panel");
  const videoPreviewWrapper = document.getElementById("video-preview-wrapper");
  const startMin = document.getElementById("start-min");
  const startSec = document.getElementById("start-sec");
  const endMin = document.getElementById("end-min");
  const endSec = document.getElementById("end-sec");
  const clipCalcDuration = document.getElementById("clip-calc-duration");
  const btnGenerate = document.getElementById("btn-generate");

  // Processing View Elements
  const stageText = document.getElementById("stage-text");

  // Complete View Elements
  const resTrackTitle = document.getElementById("res-track-title");
  const resOpBadge = document.getElementById("res-op-badge");
  const resTimeBadge = document.getElementById("res-time-badge");
  const audioPreview = document.getElementById("audio-preview");
  const btnDownload = document.getElementById("btn-download");
  const btnAdjustClip = document.getElementById("btn-adjust-clip");
  const btnConvertAnother = document.getElementById("btn-convert-another");

  // View Routing & Rendering
  function setScreen(newScreen, pushHistory = true) {
    if (state.screen === newScreen) return;
    state.screen = newScreen;
    Object.keys(views).forEach((key) => {
      if (key.toUpperCase() === newScreen) {
        views[key].classList.remove("hidden");
      } else {
        views[key].classList.add("hidden");
      }
    });

    if (pushHistory) {
      history.pushState({ screen: newScreen }, "", window.location.pathname);
    }
  }

  // Handle browser back/forward buttons (hardware back button, swipe back, browser back)
  window.addEventListener("popstate", (e) => {
    hideError();
    pauseYouTubePreview();
    const targetScreen = (e.state && e.state.screen) || "INPUT";
    if (targetScreen === "INPUT") {
      setScreen("INPUT", false);
      urlInput.focus();
      urlInput.select();
    } else {
      setScreen(targetScreen, false);
    }
  });

  // Initialize initial history entry
  history.replaceState({ screen: "INPUT" }, "", window.location.pathname);

  function showError(title, message) {
    errorTitle.textContent = title || "Error";
    errorMessage.textContent = message || "An unexpected error occurred.";
    errorBanner.classList.remove("hidden");
  }

  function hideError() {
    errorBanner.classList.add("hidden");
  }

  // Formatting helpers
  function parseTimestampToSec(str) {
    if (!str) return 0;
    const parts = str.trim().split(":").map(Number);
    if (parts.some(isNaN)) return NaN;
    if (parts.length === 1) return parts[0];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return NaN;
  }

  function formatSec(sec) {
    if (isNaN(sec) || sec < 0) return "--:--";
    const total = Math.max(0, Math.round(sec));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) {
      return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    }
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }

  function getStartTimestamp() {
    const m = (startMin.value || "0").trim();
    const s = (startSec.value || "0").trim();
    return `${m.padStart(2, "0")}:${s.padStart(2, "0")}`;
  }

  function getEndTimestamp() {
    const m = (endMin.value || "0").trim();
    const s = (endSec.value || "0").trim();
    return `${m.padStart(2, "0")}:${s.padStart(2, "0")}`;
  }

  function setTimeValues(minEl, secEl, totalSeconds) {
    if (isNaN(totalSeconds) || totalSeconds < 0) return;
    const total = Math.max(0, Math.round(totalSeconds));
    const m = Math.floor(total / 60);
    const s = total % 60;
    minEl.value = m.toString().padStart(2, "0");
    secEl.value = s.toString().padStart(2, "0");
    updateClipSummary();
  }

  function parseFormattedDurationToSegments(durStr, minEl, secEl) {
    const sec = parseTimestampToSec(durStr);
    if (!isNaN(sec)) {
      setTimeValues(minEl, secEl, sec);
    }
  }

  // --- Deterministic YouTube API & Player Lifecycle ---

  let ytApiPromise = null;
  function loadYouTubeApi() {
    if (window.YT && window.YT.Player) {
      state.ytApiReady = true;
      state.ytApiLoading = false;
      return Promise.resolve(window.YT);
    }

    if (ytApiPromise) return ytApiPromise;

    state.ytApiLoading = true;

    ytApiPromise = new Promise((resolve, reject) => {
      // YouTube calls window.onYouTubeIframeAPIReady when script initializes
      window.onYouTubeIframeAPIReady = () => {
        state.ytApiReady = true;
        state.ytApiLoading = false;
        console.log("[YT Lifecycle] YouTube IFrame API Ready");
        resolve(window.YT);
      };

      // Load script if not already added
      const existingTag = document.querySelector('script[src*="youtube.com/iframe_api"]');
      if (!existingTag) {
        const tag = document.createElement("script");
        tag.src = "https://www.youtube.com/iframe_api";
        tag.onerror = (err) => {
          state.ytApiLoading = false;
          console.error("[YT Lifecycle] Failed to load YouTube iframe_api script", err);
          reject(new Error("Failed to load YouTube player library."));
        };
        document.head.appendChild(tag);
      }
    });

    return ytApiPromise;
  }

  async function loadYouTubePreview(videoId) {
    if (!videoId) return;

    state.ytPlayerReady = false;
    state.ytPlayerLoading = true;

    // Ensure wrapper is visible when starting
    if (videoPreviewWrapper) {
      videoPreviewWrapper.classList.remove("hidden");
    }

    const frame = document.querySelector(".video-player-frame");
    if (frame) {
      frame.innerHTML = '<div id="yt-player-slot"></div>';
    }

    try {
      const YT = await loadYouTubeApi();

      state.ytPlayer = new YT.Player("yt-player-slot", {
        videoId: videoId,
        playerVars: {
          enablejsapi: 1,
          playsinline: 1,
          rel: 0,
          modestbranding: 1,
        },
        events: {
          onReady: (event) => {
            state.ytPlayerLoading = false;
            // Verify player API responsiveness immediately
            try {
              const testTime = event.target.getCurrentTime();
              console.log("[YT Lifecycle] Player verified onReady. Initial time:", testTime);
              state.ytPlayerReady = true;
            } catch (err) {
              console.warn("[YT Lifecycle] onReady fired but getCurrentTime() failed:", err);
              state.ytPlayerReady = false;
            }
          },
          onError: (event) => {
            state.ytPlayerLoading = false;
            state.ytPlayerReady = false;
            console.log("[YT Lifecycle] Embedding restricted or failed (code " + event.data + "). Hiding preview, keeping original flow.");

            // Hide the embedded video player wrapper completely to maintain the original clean flow
            if (videoPreviewWrapper) {
              videoPreviewWrapper.classList.add("hidden");
            }
          },
        },
      });
    } catch (err) {
      state.ytPlayerLoading = false;
      state.ytPlayerReady = false;
      console.log("[YT Lifecycle] Failed to initialize preview. Hiding preview, keeping original flow:", err);

      // Hide the embedded video player wrapper completely
      if (videoPreviewWrapper) {
        videoPreviewWrapper.classList.add("hidden");
      }
    }
  }

  function pauseYouTubePreview() {
    if (state.ytPlayer && typeof state.ytPlayer.pauseVideo === "function") {
      try {
        state.ytPlayer.pauseVideo();
      } catch (e) {
        console.warn("[YT Lifecycle] Error pausing video:", e);
      }
    }
  }

  function getPlayerCurrentTime() {
    if (!state.ytPlayerReady || !state.ytPlayer) {
      return { time: null, error: state.ytPlayerLoading ? "loading" : "not_ready" };
    }

    if (typeof state.ytPlayer.getCurrentTime !== "function") {
      return { time: null, error: "no_method" };
    }

    try {
      const t = state.ytPlayer.getCurrentTime();
      if (typeof t === "number" && !isNaN(t)) {
        return { time: t, error: null };
      }
      return { time: null, error: "invalid_value" };
    } catch (error) {
      console.warn("[YT Lifecycle] Failed to read YouTube player time:", error);
      return { time: null, error: "exception", details: error };
    }
  }

  function flashButtonSuccess(btn) {
    if (!btn) return;
    btn.classList.add("success-flash");
    setTimeout(() => {
      btn.classList.remove("success-flash");
    }, 600);
  }

  function updateClipSummary() {
    const startSecVal = parseTimestampToSec(getStartTimestamp());
    const endSecVal = parseTimestampToSec(getEndTimestamp());
    if (!isNaN(startSecVal) && !isNaN(endSecVal) && endSecVal > startSecVal) {
      clipCalcDuration.textContent = formatSec(endSecVal - startSecVal);
    } else {
      clipCalcDuration.textContent = "--:--";
    }
  }

  // --- Event Listeners ---

  btnDismissError.addEventListener("click", hideError);

  // 1. Inspect Form Submit
  inspectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError();

    const rawUrl = urlInput.value.trim();
    if (!rawUrl) return;

    btnInspect.disabled = true;
    btnInspectText.textContent = "Inspecting...";

    try {
      const response = await fetch("/api/inspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: rawUrl }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Inspection failed.");
      }

      state.source = data;

      // Populate Configure View
      mediaThumb.src = data.thumbnail_url;
      mediaTitle.textContent = data.title;
      mediaChannel.textContent = data.channel;
      mediaDuration.textContent = data.duration_formatted;

      // Initialize segmented timestamps: Start 00:00, End = video duration
      setTimeValues(startMin, startSec, 0);
      parseFormattedDurationToSegments(data.duration_formatted, endMin, endSec);
      updateClipSummary();

      // Reset operation to Full
      setOperation("full");

      setScreen("CONFIGURE");
    } catch (err) {
      showError("Inspection Failed", err.message);
    } finally {
      btnInspect.disabled = false;
      btnInspectText.textContent = "Inspect";
    }
  });

  // Back button to change URL
  btnBackInput.addEventListener("click", () => {
    hideError();
    pauseYouTubePreview();
    if (window.history.length > 1) {
      window.history.back();
    } else {
      setScreen("INPUT");
      urlInput.focus();
      urlInput.select();
    }
  });

  // Operation selection logic
  function setOperation(op) {
    state.operation = op;
    if (op === "full") {
      optFull.checked = true;
      cardOptFull.classList.add("active");
      cardOptClip.classList.remove("active");
      clipConfigPanel.classList.add("hidden");
      pauseYouTubePreview();
    } else {
      optClip.checked = true;
      cardOptClip.classList.add("active");
      cardOptFull.classList.remove("active");
      clipConfigPanel.classList.remove("hidden");
      updateClipSummary();
      if (state.source && state.source.video_id) {
        loadYouTubePreview(state.source.video_id);
      }
    }
  }

  cardOptFull.addEventListener("click", () => setOperation("full"));
  cardOptClip.addEventListener("click", () => setOperation("clip"));

  // Segmented input auto-advance and numeric sanitization
  function setupSegmentInput(minInput, secInput) {
    [minInput, secInput].forEach((input) => {
      input.addEventListener("input", () => {
        // Strip non-digits
        input.value = input.value.replace(/\D/g, "");
        updateClipSummary();
      });
      input.addEventListener("blur", () => {
        // Pad single digits on blur
        if (input.value.trim() !== "") {
          input.value = input.value.trim().padStart(2, "0");
        } else {
          input.value = "00";
        }
        updateClipSummary();
      });
    });

    // Auto-advance to seconds when 2 digits typed in minutes
    minInput.addEventListener("keyup", (e) => {
      if (minInput.value.length >= 2 && !["Backspace", "ArrowLeft", "Tab"].includes(e.key)) {
        secInput.focus();
        secInput.select();
      }
    });

    // Backspace from seconds into minutes when empty
    secInput.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && secInput.value.length === 0) {
        minInput.focus();
      }
    });
  }

  setupSegmentInput(startMin, startSec);
  setupSegmentInput(endMin, endSec);

  // 2. Generate MP3 Submit
  btnGenerate.addEventListener("click", async () => {
    hideError();
    pauseYouTubePreview();

    const payload = {
      source_id: state.source.source_id,
      operation: state.operation,
    };

    if (state.operation === "clip") {
      const s = getStartTimestamp();
      const e = getEndTimestamp();
      if (!s || !e) {
        showError("Invalid Input", "Please specify both start and end timestamps.");
        return;
      }
      payload.start = s;
      payload.end = e;
    }

    setScreen("PROCESSING");
    stageText.textContent = "Processing...";

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to start job.");
      }

      state.job = data;
      startPolling(data.job_id);
    } catch (err) {
      showError("Job Creation Failed", err.message);
      setScreen("CONFIGURE");
    }
  });

  // Polling Job Status
  function startPolling(jobId) {
    if (state.pollInterval) clearInterval(state.pollInterval);

    state.pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) {
          throw new Error("Failed to fetch job status.");
        }
        const data = await res.json();
        updateProcessingStage(data);

        if (data.status === "completed") {
          clearInterval(state.pollInterval);
          onJobComplete(data);
        } else if (data.status === "failed") {
          clearInterval(state.pollInterval);
          showError("Processing Failed", data.error || "Could not complete MP3 creation.");
          setScreen("CONFIGURE");
        }
      } catch (err) {
        clearInterval(state.pollInterval);
        showError("Communication Error", err.message);
        setScreen("CONFIGURE");
      }
    }, 1000);
  }

  function updateProcessingStage(jobData) {
    stageText.textContent = jobData.message;
  }

  function onJobComplete(jobData) {
    resTrackTitle.textContent = state.source.title;
    resOpBadge.textContent = state.operation === "clip" ? "Clip" : "Full Track";
    resTimeBadge.textContent =
      state.operation === "clip"
        ? `${getStartTimestamp()} ➜ ${getEndTimestamp()}`
        : state.source.duration_formatted;

    // Load stream into audio preview player
    audioPreview.src = `/api/jobs/${jobData.job_id}/stream`;
    audioPreview.load();

    if (state.operation === "clip") {
      resTimeBadge.classList.add("clickable-badge");
      resTimeBadge.title = "Click to adjust timestamps";
    } else {
      resTimeBadge.classList.remove("clickable-badge");
      resTimeBadge.removeAttribute("title");
    }

    btnDownload.href = jobData.download_url;
    setScreen("COMPLETE");
  }

  // 3. Adjust Timestamps
  function handleAdjustClip() {
    hideError();
    audioPreview.pause();
    setScreen("CONFIGURE");
    setOperation("clip");
    updateClipSummary();
    startMin.focus();
    startMin.select();
  }

  btnAdjustClip.addEventListener("click", handleAdjustClip);
  resTimeBadge.addEventListener("click", () => {
    if (state.operation === "clip") {
      handleAdjustClip();
    }
  });

  // 4. Convert Another
  btnConvertAnother.addEventListener("click", () => {
    hideError();
    audioPreview.pause();
    audioPreview.removeAttribute("src");
    audioPreview.load();
    urlInput.value = "";
    state.source = null;
    state.job = null;
    setScreen("INPUT");
  });
})();
