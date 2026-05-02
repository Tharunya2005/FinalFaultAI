/* ============================================
   FaultAI — FRONTEND JAVASCRIPT
   Handles UI interactions & communicates
   with the Python backend via fetch() API
   ============================================ */


// ──────────────────────────────────────────────
// SECTION 1: CONFIGURATION & GLOBAL VARIABLES
// ──────────────────────────────────────────────

const BACKEND_URL = "http://localhost:5000";   // Python Flask backend URL

let diagnosisHistory = [];                      // In-memory diagnosis history
let xaiApiKey = localStorage.getItem("xaiApiKey") || null;  // Stored API key
let currentKBPage = 1;                          // Knowledge base pagination


// ──────────────────────────────────────────────
// SECTION 2: TAILWIND INITIALIZATION
// ──────────────────────────────────────────────

function initializeTailwind() {
    tailwind.config = {
        content: [],
        theme: { extend: {} }
    };
}


// ──────────────────────────────────────────────
// SECTION 3: SECTION / PAGE NAVIGATION
// ──────────────────────────────────────────────

function showSection(section) {
    // Hide all sections
    document.querySelectorAll("section").forEach(s => s.classList.add("hidden"));
    // Show selected section
    document.getElementById(section).classList.remove("hidden");

    // Re-render dynamic content when navigating
    if (section === "knowledge") renderKnowledgeBase();
    if (section === "history") renderHistory();
}


// ──────────────────────────────────────────────
// SECTION 4: SYMPTOM CHIPS (Quick Select)
// ──────────────────────────────────────────────

function renderSymptomChips() {
    const container = document.getElementById("symptom-chips");
    const commonSymptoms = [
        "Pump whining noise", "Low system pressure", "Overheating oil",
        "Foamy hydraulic fluid", "Cylinder drift", "Valve sticking",
        "Slow actuator movement", "Oil leaking", "Pressure fluctuations",
        "Excessive vibration", "Cavitation noise", "Filter clogged"
    ];

    container.innerHTML = commonSymptoms.map(sym => `
        <div onclick="toggleChip(this)" 
             class="symptom-chip cursor-pointer text-xs border border-white/30 hover:border-cyan-400 px-5 py-2 rounded-3xl">
            ${sym}
        </div>
    `).join("");
}

function toggleChip(el) {
    el.classList.toggle("active");

    // Add/remove symptom from textarea
    const textarea = document.getElementById("symptoms-input");
    const symptom = el.textContent.trim();

    if (el.classList.contains("active")) {
        textarea.value += (textarea.value ? ", " : "") + symptom;
    } else {
        textarea.value = textarea.value
            .split(", ")
            .filter(s => s !== symptom)
            .join(", ");
    }
}


// ──────────────────────────────────────────────
// SECTION 5: KNOWLEDGE BASE DISPLAY (PDF Chunks)
// ──────────────────────────────────────────────

async function renderKnowledgeBase(page = 1) {
    const container = document.getElementById("kb-grid");
    const infoEl = document.getElementById("kb-info");
    const paginationEl = document.getElementById("kb-pagination");
    currentKBPage = page;

    // Show loading
    container.innerHTML = `<div class="col-span-3 text-center py-10 text-gray-400">
        <i class="fa-solid fa-spinner animate-spin text-2xl"></i>
        <p class="mt-4">Loading knowledge base from PDF...</p>
    </div>`;

    try {
        // ── FETCH FROM PYTHON BACKEND ──
        const response = await fetch(`${BACKEND_URL}/api/knowledge-base?page=${page}&per_page=12`);
        const data = await response.json();

        // Update info
        infoEl.innerHTML = `
            <div class="flex items-center gap-x-2">
                <i class="fa-solid fa-file-pdf text-red-400"></i>
                <span>${data.source.filename}</span>
            </div>
            <div class="mt-1">${data.total} chunks indexed</div>
        `;

        // Render chunk cards
        container.innerHTML = data.chunks.map(chunk => `
            <div class="glass border border-white/10 rounded-3xl p-6 card-hover">
                <div class="flex justify-between text-xs mb-3">
                    <span class="px-4 py-1 bg-white/10 rounded-3xl">
                        <i class="fa-solid fa-file-lines mr-1"></i>
                        Pages ${chunk.page_start}${chunk.page_end !== chunk.page_start ? '-' + chunk.page_end : ''}
                    </span>
                    <span class="text-gray-400">${chunk.word_count} words</span>
                </div>
                <div class="text-sm text-gray-300 line-clamp-4 mb-4 leading-relaxed">${chunk.preview}</div>
                <div class="text-xs flex items-center gap-x-2 text-cyan-400">
                    <i class="fa-solid fa-cube"></i>
                    Chunk #${chunk.chunk_id}
                </div>
            </div>
        `).join("");

        // Render pagination
        if (data.total_pages > 1) {
            let paginationHTML = '';

            // Previous button
            if (page > 1) {
                paginationHTML += `<button onclick="renderKnowledgeBase(${page - 1})" class="px-4 py-2 bg-white/10 rounded-xl hover:bg-white/20 text-sm">
                    <i class="fa-solid fa-chevron-left"></i> Prev
                </button>`;
            }

            // Page indicator
            paginationHTML += `<span class="text-sm text-gray-400">Page ${page} of ${data.total_pages}</span>`;

            // Next button
            if (page < data.total_pages) {
                paginationHTML += `<button onclick="renderKnowledgeBase(${page + 1})" class="px-4 py-2 bg-white/10 rounded-xl hover:bg-white/20 text-sm">
                    Next <i class="fa-solid fa-chevron-right"></i>
                </button>`;
            }

            paginationEl.innerHTML = paginationHTML;
        } else {
            paginationEl.innerHTML = '';
        }

    } catch (err) {
        container.innerHTML = `<div class="col-span-3 text-center py-10 text-red-400">
            <i class="fa-solid fa-triangle-exclamation text-2xl"></i>
            <p class="mt-4">Cannot connect to backend. Make sure Python server is running.</p>
            <code class="text-xs text-gray-500 mt-2 block">python app.py</code>
        </div>`;
    }
}


// ──────────────────────────────────────────────
// SECTION 6: DIAGNOSIS HISTORY
// ──────────────────────────────────────────────

function renderHistory() {
    const container = document.getElementById("history-list");

    if (diagnosisHistory.length === 0) {
        container.innerHTML = `
        <div class="text-center py-20 text-gray-400">
            <i class="fa-solid fa-clock text-6xl mb-6 opacity-30"></i>
            <p>No diagnoses yet. Start your first one above!</p>
        </div>`;
        return;
    }

    container.innerHTML = diagnosisHistory.map((entry, i) => `
        <div onclick="loadOldDiagnosis(${i})" class="glass border border-white/10 rounded-3xl p-6 flex gap-6 cursor-pointer card-hover">
            <div class="w-12 h-12 flex-shrink-0 bg-gradient-to-br from-orange-400 to-amber-500 rounded-2xl flex items-center justify-center text-3xl">⚡</div>
            <div class="flex-1">
                <div class="flex justify-between">
                    <div class="font-semibold">${entry.fault}</div>
                    <div class="text-xs text-gray-400">${entry.time}</div>
                </div>
                <p class="text-gray-400 text-sm mt-1 line-clamp-2">${entry.symptoms}</p>
                <div class="text-cyan-400 text-xs mt-4 flex items-center">
                    <i class="fa-solid fa-file-pdf mr-1"></i> Diagnosed from PDF + Grok
                    ${entry.pages ? ` &bull; Pages: ${entry.pages}` : ''}
                </div>
            </div>
        </div>
    `).join("");
}

function loadOldDiagnosis(index) {
    const entry = diagnosisHistory[index];
    showSection("diagnose");
    document.getElementById("symptoms-input").value = entry.symptoms;
    runDiagnosis();
}


// ──────────────────────────────────────────────
// SECTION 7: MAIN DIAGNOSIS — CALLS PYTHON BACKEND
// This is the CORE function that connects to xAI + RAG
// ──────────────────────────────────────────────

async function runDiagnosis() {
    const input = document.getElementById("symptoms-input").value.trim();
    const category = document.getElementById("category-select").value;

    if (!input) {
        alert("Please describe the hydraulic symptoms first!");
        return;
    }

    // ── Show loading state ──
    document.getElementById("empty-results").classList.add("hidden");
    const resultsPanel = document.getElementById("results-panel");
    resultsPanel.classList.remove("hidden");

    resultsPanel.innerHTML = `
        <div class="flex flex-col items-center justify-center py-20">
            <div class="flex items-center gap-x-4 text-cyan-400">
                <i class="fa-solid fa-spinner animate-spin text-4xl"></i>
                <div>
                    <div class="text-2xl font-medium">Searching PDF manual...</div>
                    <div class="text-sm">RAG is retrieving relevant passages, Grok is analyzing</div>
                </div>
            </div>
            <p class="text-xs text-gray-500 mt-8">This usually takes 3-8 seconds</p>
        </div>`;

    try {
        // ═══════════════════════════════════════════
        // ► FETCH CALL TO PYTHON BACKEND
        //   Sends symptoms → Backend runs PDF RAG + Grok
        //   Returns: fault, passages, solutions, page refs
        // ═══════════════════════════════════════════
        const response = await fetch(`${BACKEND_URL}/api/diagnose`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                symptoms: input,
                category: category !== "all" ? category : null,
                api_key: xaiApiKey      // API key sent to backend (not exposed in browser)
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Diagnosis failed");
        }

        // ── Render the result ──
        displayResults(result, input);

        // ── Save to history ──
        diagnosisHistory.unshift({
            id: Date.now(),
            symptoms: input,
            fault: result.fault,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            pages: result.source_pages ? result.source_pages.slice(0, 5).join(", ") : null
        });
        if (diagnosisHistory.length > 10) diagnosisHistory.pop();

    } catch (err) {
        resultsPanel.innerHTML = `
            <div class="flex flex-col items-center justify-center py-20 text-red-400">
                <i class="fa-solid fa-triangle-exclamation text-5xl mb-4"></i>
                <h3 class="text-2xl font-semibold mb-2">Diagnosis Failed</h3>
                <p class="text-sm text-gray-400 max-w-md text-center">${err.message}</p>
                <p class="text-xs text-gray-500 mt-4">Make sure the Python backend is running: <code>python app.py</code></p>
                <button onclick="resetDiagnosis()" class="mt-6 px-6 py-3 bg-white/10 rounded-3xl hover:bg-white/20 text-white text-sm">
                    Try Again
                </button>
            </div>`;
    }
}


// ──────────────────────────────────────────────
// SECTION 8: DISPLAY DIAGNOSIS RESULTS
// ──────────────────────────────────────────────

function displayResults(result, inputSymptoms) {
    const resultsPanel = document.getElementById("results-panel");

    // Build source pages display
    const pagesDisplay = result.source_pages
        ? result.source_pages.map(p => `<span class="px-2 py-1 bg-white/10 rounded-lg">${p}</span>`).join(" ")
        : "N/A";

    // Build retrieved passages HTML
    const passagesHTML = result.retrieved_passages
        ? result.retrieved_passages.map((p, i) => `
            <div class="bg-black/40 rounded-2xl p-4 border border-white/5">
                <div class="flex justify-between text-xs mb-2">
                    <span class="text-cyan-400 font-medium">
                        <i class="fa-solid fa-file-lines mr-1"></i>
                        Pages ${p.page_start}${p.page_end !== p.page_start ? '-' + p.page_end : ''}
                    </span>
                    <span class="text-emerald-400">${p.similarity_score}% match</span>
                </div>
                <p class="text-xs text-gray-400 leading-relaxed line-clamp-3">${p.text}</p>
            </div>
        `).join("")
        : "";

    resultsPanel.innerHTML = `
        <!-- Header -->
        <div class="flex justify-between mb-6">
            <div class="flex items-center">
                <i class="fa-solid fa-check-circle text-emerald-400 text-3xl mr-4"></i>
                <h3 class="text-3xl font-semibold">Diagnosis Complete</h3>
            </div>
            <button onclick="resetDiagnosis()" class="text-sm flex items-center gap-x-2 text-gray-400 hover:text-white">
                <i class="fa-solid fa-rotate-right"></i>
                NEW DIAGNOSIS
            </button>
        </div>
        
        <!-- Fault Card -->
        <div class="bg-gradient-to-br from-orange-500/10 to-amber-500/10 border border-orange-400/30 rounded-3xl p-8 mb-8">
            <div class="flex items-start gap-6">
                <div class="text-7xl">🔧</div>
                <div class="flex-1">
                    <div class="flex justify-between items-baseline">
                        <h3 class="text-4xl font-semibold">${result.fault}</h3>
                        <div class="bg-emerald-400 text-black text-sm font-bold px-5 h-8 rounded-3xl flex items-center">
                            ${result.confidence}% relevance
                        </div>
                    </div>
                    <p class="text-gray-400 mt-2">${inputSymptoms}</p>
                    <div class="mt-4 flex items-center gap-x-2 text-xs text-gray-400">
                        <i class="fa-solid fa-file-pdf text-red-400"></i>
                        Source: ${result.pdf_source || 'Vickers Hydraulics Manual'}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Source Pages -->
        <div class="mb-6">
            <h4 class="uppercase text-xs mb-3 text-gray-400 font-medium flex items-center">
                <i class="fa-solid fa-bookmark mr-2"></i> Referenced Pages
            </h4>
            <div class="flex flex-wrap gap-2 text-xs">${pagesDisplay}</div>
        </div>

        <!-- RAG Passages + Grok Solution Split -->
        <div class="grid grid-cols-2 gap-6">
            <div>
                <h4 class="uppercase text-xs mb-3 text-gray-400 font-medium flex items-center">
                    <i class="fa-solid fa-book-open mr-2"></i> Retrieved Manual Passages (RAG)
                </h4>
                <div class="space-y-3">
                    ${passagesHTML}
                </div>
            </div>
            
            <div>
                <h4 class="uppercase text-xs mb-3 text-cyan-400 font-medium flex items-center">
                    <i class="fa-solid fa-wand-magic-sparkles mr-2"></i> AI Diagnosis & Solutions (Grok)
                </h4>
                <div class="text-sm leading-relaxed bg-black/60 rounded-3xl p-6">
                    ${result.grok_solution}
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="mt-8 flex items-center justify-between text-xs">
            <div class="flex items-center gap-x-2 text-emerald-400">
                <i class="fa-solid fa-database"></i>
                Searched ${result.total_passages_searched || '—'} passages from PDF knowledge base
            </div>
            <button onclick="copyResults()" class="flex items-center gap-x-2 px-6 py-3 bg-white/10 rounded-3xl hover:bg-white/20">
                <i class="fa-solid fa-copy"></i>
                Copy full report
            </button>
        </div>`;
}


// ──────────────────────────────────────────────
// SECTION 9: RESET DIAGNOSIS
// ──────────────────────────────────────────────

function resetDiagnosis() {
    document.getElementById("results-panel").classList.add("hidden");
    document.getElementById("empty-results").classList.remove("hidden");
    document.getElementById("symptoms-input").value = "";

    // Reset all chips
    document.querySelectorAll(".symptom-chip.active").forEach(chip => {
        chip.classList.remove("active");
    });
}


// ──────────────────────────────────────────────
// SECTION 10: COPY RESULTS TO CLIPBOARD
// ──────────────────────────────────────────────

function copyResults() {
    const symptoms = document.getElementById("symptoms-input").value;
    const text = `FaultAI Diagnosis Report\n` +
        `========================\n` +
        `Symptoms: ${symptoms}\n` +
        `Source: Vickers Industrial Hydraulics Manual (PDF RAG)\n` +
        `Generated by: xAI Grok + PDF RAG Pipeline\n` +
        `Timestamp: ${new Date().toLocaleString()}`;

    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target.closest("button");
        const original = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
        setTimeout(() => btn.innerHTML = original, 1800);
    });
}


// ──────────────────────────────────────────────
// SECTION 11: DEMO MODE (Home Page Animation)
// ──────────────────────────────────────────────

function demoDiagnosis() {
    document.getElementById("demo-output").innerHTML = `
        <div class="flex items-center justify-between text-xs mb-2">
            <span class="text-cyan-400">SYMPTOMS</span>
            <span class="font-mono">PUMP WHINE • LOW PRESSURE</span>
        </div>
        <div class="text-xl font-medium mb-6">Pump cavitation detected (87% relevance)</div>
        <div class="text-xs bg-emerald-900/30 text-emerald-400 px-4 py-3 rounded-2xl flex justify-between">
            <span>Grok solution:</span> 
            <span class="font-medium">Check suction line restrictions • Inspect fluid level</span>
        </div>
        <div class="mt-4 text-[10px] text-gray-400 flex items-center justify-center">
            RAG retrieved from pages 142-145 • xAI Grok
        </div>`;

    setTimeout(() => {
        showSection('diagnose');
        document.getElementById("symptoms-input").value =
            "Hydraulic pump making loud whining noise, system pressure dropping, foamy oil in reservoir";
        runDiagnosis();
    }, 1200);
}


// ──────────────────────────────────────────────
// SECTION 12: API KEY MODAL
// ──────────────────────────────────────────────

function toggleApiModal() {
    const modal = document.getElementById("api-modal");
    modal.classList.toggle("hidden");

    if (!modal.classList.contains("hidden") && xaiApiKey) {
        document.getElementById("api-key-input").value = "••••••••••••••••••••";
        document.getElementById("api-status").innerHTML =
            `<span class="text-emerald-400">✅ Connected to xAI Grok API</span>`;
    }
}

function saveApiKey() {
    const key = document.getElementById("api-key-input").value.trim();

    if (key && key.length > 10) {
        xaiApiKey = key;
        localStorage.setItem("xaiApiKey", key);

        document.getElementById("api-status").innerHTML =
            `✅ <span class="text-emerald-400">Connected to xAI Grok API</span>
             <br><span class="text-xs">Your PDF RAG + Grok pipeline is now live!</span>`;

        setTimeout(() => toggleApiModal(), 1400);
    } else {
        document.getElementById("api-status").innerHTML =
            `<span class="text-red-400">❌ Invalid API key. Must be longer than 10 characters.</span>`;
    }
}


// ──────────────────────────────────────────────
// SECTION 13: BACKEND CONNECTION STATUS CHECK
// ──────────────────────────────────────────────

async function checkBackendStatus() {
    const statusEl = document.getElementById("backend-status");
    try {
        const res = await fetch(`${BACKEND_URL}/api/health`);
        const data = await res.json();
        if (data.status === "ok") {
            statusEl.innerHTML = `
                <div class="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
                <span class="font-medium text-emerald-400">Backend Online</span>`;

            // Update home page stats
            const chunksStat = document.getElementById("stat-chunks");
            const sourceStat = document.getElementById("stat-source");
            if (chunksStat) chunksStat.textContent = data.total_chunks || "—";
            if (sourceStat) sourceStat.textContent = data.pdf_source ? "1 PDF" : "—";
        }
    } catch {
        statusEl.innerHTML = `
            <div class="w-2 h-2 bg-red-400 rounded-full"></div>
            <span class="font-medium text-red-400">Backend Offline</span>`;
    }
}


// ──────────────────────────────────────────────
// SECTION 14: APP INITIALIZATION
// ──────────────────────────────────────────────

window.onload = function () {
    initializeTailwind();
    renderSymptomChips();
    renderHistory();
    checkBackendStatus();

    console.log('%c🚀 FaultAI Frontend loaded!', 'color:#00d4ff; font-size:13px; font-weight:600');
    console.log('%c📡 Connecting to Python backend (PDF RAG)...', 'color:#9ca3af; font-size:11px');
};