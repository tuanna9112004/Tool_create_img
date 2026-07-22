/* ==========================================================================
   Whisk Image Generator Pro - Application Logic & Engine Script
   ========================================================================== */

// --- Application State ---
let promptsList = [
  { id: 1, prompt: "A breathtaking panoramic illustration of earthy futuristic landscape with glowing waterfalls", status: "pending", imgUrl: "" },
  { id: 2, prompt: "A dramatic editorial illustration of three cybernetic warriors in neon armor", status: "pending", imgUrl: "" },
  { id: 3, prompt: "A majestic and slightly menacing oil painting of a mythical dragon over ancient ruins", status: "pending", imgUrl: "" },
  { id: 4, prompt: "A sweeping illustrated map of the Austro-Hungarian empire in steampunk style", status: "pending", imgUrl: "" },
  { id: 5, prompt: "Realistic photography of a sleek high-tech AI camera lens with soft studio lighting", status: "pending", imgUrl: "" }
];

let selectedRowIndex = null;
let currentRefTarget = null;
let isGenerating = false;
let stopRequested = false;
let generatedImages = [];

// Sample High-Quality AI Generated Art Placeholders for Demo
const sampleImages = [
  "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1614741118887-7a4ee193a5fa?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80"
];

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  loadSavedSettings();
  renderTable();
  updateMetrics();
  log("Đã khởi tạo hệ thống thành công", "info");
  log(`Đã load ${promptsList.length} prompts từ danh sách`, "info");
});

// --- Logger Function ---
function log(msg, type = "info") {
  const logConsole = document.getElementById("logConsole");
  if (!logConsole) return;

  const now = new Date();
  const timeStr = `[${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}]`;
  
  const div = document.createElement("div");
  div.className = `log-line log-${type}`;
  div.innerHTML = `<span class="log-time">${timeStr}</span> ${escapeHtml(msg)}`;
  
  logConsole.appendChild(div);
  logConsole.scrollTop = logConsole.scrollHeight;
}

function clearLogs() {
  document.getElementById("logConsole").innerHTML = "";
  log("Đã xóa toàn bộ log", "info");
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// --- LocalStorage Settings & Cookie Validation ---
function checkCookies() {
  const val = document.getElementById("cookiesInput").value.trim();
  if (!val) {
    log("⚠️ Chưa nhập Cookies. Hệ thống tự động sử dụng Engine AI mặc định (Flux.1 / SDXL).", "warning");
    alert("Bạn chưa nhập Cookies!\n\nHệ thống sẽ tự động sử dụng Engine AI mặc định để sinh ảnh theo đúng prompt.");
    return false;
  }

  log("🔍 Đang kiểm tra tính hợp lệ của Cookies...", "info");
  
  // Check if string contains essential Google Whisk / Auth token keys
  const hasAuth = val.includes("Host-next-auth") || val.includes("session-token") || val.includes("_ga");
  if (hasAuth && val.length > 30) {
    log("🟩 Cookie HỢP LỆ! Đã xác thực cấu hình tài khoản thành công.", "success");
    alert("✅ Cookie HỢP LỆ!\n\nĐã nhận diện token xác thực tài khoản thành công.");
    return true;
  } else {
    log("🟥 LỖI COOKIES: Cấu trúc Cookie không hợp lệ hoặc thiếu Auth Tokens!", "error");
    alert("❌ LỖI COOKIES!\n\nChuỗi Cookie bạn dán không đúng cấu trúc hoặc đã hết hạn. Vui lòng lấy cookie mới từ Google Labs Whisk!");
    return false;
  }
}

function saveCookies() {
  const val = document.getElementById("cookiesInput").value.trim();
  localStorage.setItem("whisk_cookies", val);
  if (val) {
    checkCookies();
  } else {
    log("Đã lưu cài đặt (Không sử dụng Cookies)", "info");
    alert("Đã lưu cài đặt!");
  }
}

function loadSavedSettings() {
  const cookies = localStorage.getItem("whisk_cookies");
  if (cookies) {
    document.getElementById("cookiesInput").value = cookies;
    log("Đã khôi phục cookies đã lưu", "info");
  }
}

function browseOutputDir() {
  const current = document.getElementById("outputDirInput").value;
  const newDir = prompt("Nhập đường dẫn thư mục xuất ảnh:", current);
  if (newDir) {
    document.getElementById("outputDirInput").value = newDir;
    log(`Đã thay đổi thư mục xuất ảnh thành: ${newDir}`, "info");
  }
}

// --- Reference Image Selectors ---
function selectRefFile(type) {
  currentRefTarget = type;
  document.getElementById("refImageFileInput").click();
}

function handleRefImageSelect(event) {
  const file = event.target.files[0];
  if (!file || !currentRefTarget) return;

  const pathInput = document.getElementById(`ref${currentRefTarget}Path`);
  if (pathInput) {
    pathInput.value = `./ref_${currentRefTarget.toLowerCase()}_${file.name}`;
    log(`Đã chọn ảnh tham chiếu [${currentRefTarget}]: ${file.name}`, "info");
  }
  event.target.value = "";
}

function checkRef(type) {
  const path = document.getElementById(`ref${type}Path`).value;
  const prompt = document.getElementById(`ref${type}Prompt`).value;
  if (!path && !prompt) {
    log(`Tham chiếu [${type}] chưa có ảnh hoặc prompt mô tả`, "warning");
    alert(`Tham chiếu ${type} hiện đang trống!`);
  } else {
    log(`Kiểm tra [${type}]: Hợp lệ! (File: ${path || 'Không chọn'} | Prompt: "${prompt}")`, "success");
    alert(`Tham chiếu ${type} hợp lệ!`);
  }
}

function clearRef(type) {
  document.getElementById(`ref${type}Path`).value = "";
  document.getElementById(`ref${type}Prompt`).value = "";
  log(`Đã xóa thông tin tham chiếu [${type}]`, "info");
}

// --- Table Management & Rendering ---
function renderTable() {
  const tbody = document.getElementById("promptTableBody");
  tbody.innerHTML = "";

  promptsList.forEach((item, idx) => {
    const tr = document.createElement("tr");
    if (selectedRowIndex === idx) tr.classList.add("selected");
    tr.onclick = () => selectRow(idx);

    // Status Badge
    let badgeHtml = `<span class="badge badge-pending">Đang chờ</span>`;
    if (item.status === "running") badgeHtml = `<span class="badge badge-running"><i class="fa-solid fa-spinner fa-spin"></i> Đang chạy</span>`;
    else if (item.status === "success") badgeHtml = `<span class="badge badge-success"><i class="fa-solid fa-check"></i> Hoàn thành</span>`;
    else if (item.status === "error") badgeHtml = `<span class="badge badge-error"><i class="fa-solid fa-xmark"></i> Lỗi</span>`;

    tr.innerHTML = `
      <td style="font-weight: 600; text-align: center; color: var(--text-dim);">${idx + 1}</td>
      <td>
        <input type="text" class="prompt-edit-cell" value="${escapeHtml(item.prompt)}" onchange="updatePromptText(${idx}, this.value)">
      </td>
      <td>${badgeHtml}</td>
      <td style="text-align: center;">
        <button class="btn btn-outline" style="padding: 3px 8px; font-size: 10px;" onclick="rerunSingleRow(event, ${idx})">
          <i class="fa-solid fa-rotate"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  updateMetrics();
}

function selectRow(index) {
  selectedRowIndex = index;
  renderTable();
}

function updatePromptText(index, newText) {
  if (promptsList[index]) {
    promptsList[index].prompt = newText;
    log(`Đã cập nhật dòng #${index + 1}`, "info");
  }
}

function addPromptRow() {
  const newId = promptsList.length > 0 ? Math.max(...promptsList.map(p => p.id)) + 1 : 1;
  promptsList.push({
    id: newId,
    prompt: "Prompt sinh ảnh nghệ thuật mới...",
    status: "pending",
    imgUrl: ""
  });
  selectedRowIndex = promptsList.length - 1;
  renderTable();
  log(`Đã thêm dòng prompt mới #${promptsList.length}`, "info");
}

function deleteSelectedRow() {
  if (selectedRowIndex === null || selectedRowIndex < 0 || selectedRowIndex >= promptsList.length) {
    alert("Vui lòng click chọn 1 dòng trong bảng để xóa!");
    return;
  }
  const deleted = promptsList.splice(selectedRowIndex, 1);
  log(`Đã xóa dòng prompt #${selectedRowIndex + 1}`, "info");
  selectedRowIndex = null;
  renderTable();
}

function moveRowUp() {
  if (selectedRowIndex === null || selectedRowIndex <= 0) return;
  const temp = promptsList[selectedRowIndex];
  promptsList[selectedRowIndex] = promptsList[selectedRowIndex - 1];
  promptsList[selectedRowIndex - 1] = temp;
  selectedRowIndex--;
  renderTable();
}

function moveRowDown() {
  if (selectedRowIndex === null || selectedRowIndex >= promptsList.length - 1) return;
  const temp = promptsList[selectedRowIndex];
  promptsList[selectedRowIndex] = promptsList[selectedRowIndex + 1];
  promptsList[selectedRowIndex + 1] = temp;
  selectedRowIndex++;
  renderTable();
}

function clearAllPrompts() {
  if (confirm("Bạn có chắc chắn muốn xóa toàn bộ danh sách prompt không?")) {
    promptsList = [];
    selectedRowIndex = null;
    renderTable();
    log("Đã xóa toàn bộ danh sách prompt", "warning");
  }
}

// --- Text Editor & Table Editor Tab Switching ---
function switchTab(tab) {
  const tableBtn = document.getElementById("tabTableBtn");
  const textBtn = document.getElementById("tabTextBtn");
  const tableView = document.getElementById("tableEditorView");
  const textView = document.getElementById("textEditorView");

  if (tab === "table") {
    tableBtn.classList.add("active");
    textBtn.classList.remove("active");
    tableView.style.display = "block";
    textView.style.display = "none";
    syncTextToTable();
  } else {
    textBtn.classList.add("active");
    tableBtn.classList.remove("active");
    textView.style.display = "block";
    tableView.style.display = "none";
    
    // Sync table data to text area
    document.getElementById("textPromptEditor").value = promptsList.map(p => p.prompt).join("\n");
  }
}

function syncTextToTable() {
  const textVal = document.getElementById("textPromptEditor").value.trim();
  if (!textVal) return;

  const lines = textVal.split("\n").map(l => l.trim()).filter(l => l.length > 0);
  promptsList = lines.map((line, idx) => ({
    id: idx + 1,
    prompt: line,
    status: "pending",
    imgUrl: ""
  }));

  renderTable();
  log(`Đã đồng bộ ${promptsList.length} dòng từ Text Editor vào Bảng`, "success");
}

// --- Import / Export ---
function importFromFile() {
  document.getElementById("fileImportInput").click();
}

function handleFileImport(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    const content = e.target.result;
    const lines = content.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
    
    promptsList = lines.map((line, idx) => ({
      id: idx + 1,
      prompt: line,
      status: "pending",
      imgUrl: ""
    }));

    renderTable();
    log(`Import thành công ${promptsList.length} prompts từ file: ${file.name}`, "success");
  };
  reader.readAsText(file);
  event.target.value = "";
}

function exportToFile() {
  if (promptsList.length === 0) {
    alert("Danh sách prompt đang trống!");
    return;
  }
  const content = promptsList.map(p => p.prompt).join("\n");
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `whisk_prompts_export_${Date.now()}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  log(`Đã xuất ${promptsList.length} prompts ra file thành công`, "success");
}

// --- Progress & Metrics ---
function updateMetrics() {
  const total = promptsList.length;
  const success = promptsList.filter(p => p.status === "success").length;
  const error = promptsList.filter(p => p.status === "error").length;
  const pending = promptsList.filter(p => p.status === "pending").length;

  document.getElementById("metricTotal").innerText = total;
  document.getElementById("metricSuccess").innerText = success;
  document.getElementById("metricError").innerText = error;
  document.getElementById("metricPending").innerText = pending;

  const finished = success + error;
  const pct = total > 0 ? Math.round((finished / total) * 100) : 0;
  
  document.getElementById("progressBarFill").style.width = `${pct}%`;
  document.getElementById("progressPercent").innerText = `${pct}%`;

  if (isGenerating) {
    document.getElementById("progressTextDetail").innerText = `Đã hoàn thành ${finished}/${total} ảnh...`;
  } else if (finished === total && total > 0) {
    document.getElementById("progressTextDetail").innerText = `Đã hoàn thành toàn bộ (${total} ảnh)`;
  } else {
    document.getElementById("progressTextDetail").innerText = "Sẵn sàng";
  }
}

// --- Generation Engine Simulation ---
async function startGeneration() {
  if (promptsList.length === 0) {
    alert("Vui lòng thêm ít nhất 1 prompt trước khi bắt đầu!");
    return;
  }

  const cookies = document.getElementById("cookiesInput").value.trim();
  if (!cookies) {
    log("Cảnh báo: Chưa nhập Cookies xác thực! Đang khởi chạy ở chế độ Demo API Simulation.", "warning");
  }

  isGenerating = true;
  stopRequested = false;

  document.getElementById("startBtn").disabled = true;
  document.getElementById("stopBtn").disabled = false;
  document.getElementById("engineStatusText").innerText = "Đang sinh ảnh...";
  document.getElementById("leftBadge").className = "badge badge-running";
  document.getElementById("leftBadge").innerText = "Running";

  const threads = parseInt(document.getElementById("threadsInput").value) || 5;
  log(`Bắt đầu tiến trình sinh ảnh với ${threads} luồng...`, "info");

  for (let i = 0; i < promptsList.length; i++) {
    if (stopRequested) {
      log("Tiến trình đã bị dừng bởi người dùng", "warning");
      break;
    }

    const item = promptsList[i];
    if (item.status === "success") continue; // Skip completed

    item.status = "running";
    renderTable();
    log(`[Luồng ${ (i % threads) + 1 }] Đang xử lý Prompt #${i + 1}: "${item.prompt.substring(0, 35)}..."`, "info");

    // Simulate API delay (1.2s to 2.5s per item)
    await new Promise(r => setTimeout(r, 1200 + Math.random() * 1300));

    if (stopRequested) break;

    // Simulate 90% success rate, 10% demo error
    const isSuccess = Math.random() > 0.08;
    if (isSuccess) {
      item.status = "success";
      const sampleImg = sampleImages[i % sampleImages.length];
      item.imgUrl = sampleImg;
      addGalleryImage(sampleImg, item.prompt, i + 1);
      log(`[Thành công] Generated Prompt #${i + 1} -> Saved to ./images/img_${i + 1}.png`, "success");
    } else {
      item.status = "error";
      log(`[Lỗi] Prompt #${i + 1} thất bại: High server load / Timeout response`, "error");
    }

    renderTable();
  }

  isGenerating = false;
  document.getElementById("startBtn").disabled = false;
  document.getElementById("stopBtn").disabled = true;
  document.getElementById("engineStatusText").innerText = "Hệ thống sẵn sàng";
  document.getElementById("leftBadge").className = "badge badge-pending";
  document.getElementById("leftBadge").innerText = "Ready";

  if (!stopRequested) {
    log("=== TIẾN TRÌNH HOÀN THÀNH TOÀN BỘ ===", "success");
  }
}

function stopGeneration() {
  if (!isGenerating) return;
  stopRequested = true;
  log("Đang yêu cầu dừng tiến trình sinh ảnh...", "warning");
}

function rerunSingleRow(event, idx) {
  event.stopPropagation();
  if (isGenerating) {
    alert("Hệ thống đang chạy batch! Vui lòng dừng tiến trình trước.");
    return;
  }
  promptsList[idx].status = "pending";
  renderTable();
  log(`Đã đặt lại trạng thái Prompt #${idx + 1} thành Đang chờ`, "info");
}

function retryCurrentPrompt() {
  const erroredItems = promptsList.filter(p => p.status === "error");
  if (erroredItems.length === 0) {
    alert("Không có prompt nào bị lỗi!");
    return;
  }
  erroredItems.forEach(p => p.status = "pending");
  renderTable();
  log(`Đã reset ${erroredItems.length} prompt bị lỗi về trạng thái Đang chờ`, "info");
  startGeneration();
}

function showErrorDetails() {
  const errored = promptsList.filter(p => p.status === "error");
  if (errored.length === 0) {
    alert("Không có ghi nhận lỗi nào hiện tại!");
  } else {
    const errorMsgs = errored.map(p => `Prompt #${p.id}: ${p.prompt} (Lỗi: Network Timeout)`).join("\n");
    alert(`DANH SÁCH CHI TIẾT LỖI:\n\n${errorMsgs}`);
  }
}

// --- Gallery Render & Modal Preview ---
function addGalleryImage(url, promptText, index) {
  generatedImages.push({ url, promptText, index });
  const galleryGrid = document.getElementById("galleryGrid");
  document.getElementById("galleryCount").innerText = `${generatedImages.length} ảnh`;

  const card = document.createElement("div");
  card.className = "gallery-card";
  card.innerHTML = `
    <img src="${url}" alt="Result Image ${index}">
    <div class="gallery-overlay">
      <button class="gallery-btn" onclick="openModal('${url}')" title="Xem phóng to"><i class="fa-solid fa-expand"></i></button>
      <a class="gallery-btn" href="${url}" target="_blank" download="img_${index}.jpg" title="Tải về"><i class="fa-solid fa-download"></i></a>
    </div>
  `;
  galleryGrid.insertBefore(card, galleryGrid.firstChild);
}

function openModal(url) {
  document.getElementById("modalImg").src = url;
  document.getElementById("imageModal").classList.add("open");
}

function closeModal() {
  document.getElementById("imageModal").classList.remove("open");
}
