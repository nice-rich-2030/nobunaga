let appData = {
    daimyo: [],
    generals: [],
    backgrounds: []
};

// DOM Elements (Updated)
const categorySelect = document.getElementById('category-select');
const targetSelect = document.getElementById('target-select');
const targetIdValue = document.getElementById('target-id-value');
const targetSizeValue = document.getElementById('target-size-value');
const promptInput = document.getElementById('prompt-input');
const generateBtn = document.getElementById('generate-btn');
const imageGallery = document.getElementById('image-gallery');

// Modal Elements
const selectionOverlay = document.getElementById('selection-overlay');
const confirmReflectBtn = document.getElementById('confirm-reflect-btn');
const cancelReflectBtn = document.getElementById('cancel-reflect-btn');
const destPathPreview = document.getElementById('dest-path-preview');
const selectedImagePreview = document.getElementById('selected-image-preview');
const modalCategorySelect = document.getElementById('modal-category-select');
const modalTargetSelect = document.getElementById('modal-target-select');

let selectedImageFile = null;

// Initialize
async function init() {
    await fetchData();
    updateTargetList(); // Main list
    fetchImages();
}

async function fetchData() {
    const res = await fetch('/api/data');
    appData = await res.json();
}

const categoryMap = {
    'daimyo': 'daimyo',
    'general': 'generals',
    'background': 'backgrounds'
};

function updateTargetList() {
    const categoryValue = categorySelect.value;
    const apiKey = categoryMap[categoryValue];
    const targets = appData[apiKey] || [];

    targetSelect.innerHTML = '';
    targets.forEach(t => {
        const option = document.createElement('option');
        option.value = t.id;
        option.textContent = categoryValue === 'background' ? t.name : `${t.clan || ''} ${t.name}`.trim();
        targetSelect.appendChild(option);
    });

    updateTargetInfo();
}

function updateTargetInfo() {
    const categoryValue = categorySelect.value;
    const targetId = targetSelect.value;
    const apiKey = categoryMap[categoryValue];
    const targets = appData[apiKey] || [];
    const target = targets.find(t => t.id == targetId);

    // Auto-fill Template Prompt
    let targetName = "";
    if (target) {
        targetName = categoryValue === 'background' ? target.name : `${target.clan || ''} ${target.name}`.trim();
        targetIdValue.textContent = target.id;
        if (categoryValue === 'background') {
            targetSizeValue.textContent = '1280 x 720';
            promptInput.value = `戦国時代の背景。${targetName}の風景。`;
        } else {
            targetSizeValue.textContent = '256 x 256';
            //promptInput.value = `戦国時代の${categoryValue === 'daimyo' ? '大名' : '武将'}ポートレート。${targetName}の顔。プロの漫画調。魅力的で美しい女子の将軍`;
            promptInput.value = `戦国時代の${categoryValue === 'daimyo' ? '大名' : '武将'}である${targetName}の娘の美しい女子の将軍のポートレート。高精細な漫画調`;
        }
    } else {
        targetIdValue.textContent = '-';
        targetSizeValue.textContent = '-';
        promptInput.value = "";
    }
}

async function fetchImages() {
    const res = await fetch('/api/images');
    const images = await res.json();

    imageGallery.innerHTML = '';
    images.forEach(imgData => {
        const div = document.createElement('div');
        div.className = 'gallery-item';

        // imgData is now { filename, prompt, target_name, category }
        // or just filename string (backward compatibility)
        const filename = imgData.filename || imgData;
        const promptText = imgData.prompt || "(No prompt)";
        const infoText = imgData.target_name ? `[${imgData.category}] ${imgData.target_name}` : "";

        div.innerHTML = `
            <img src="/assets-test/${filename}" alt="${filename}">
            <div class="gallery-info">
                <div class="gallery-target">${infoText}</div>
                <div class="gallery-prompt" title="${promptText}">${promptText}</div>
            </div>
        `;
        div.onclick = () => showReflectModal(filename, imgData);
        imageGallery.appendChild(div);
    });
}

// Populate Modal Dropdowns
function updateModalTargetList() {
    const categoryValue = modalCategorySelect.value;
    const apiKey = categoryMap[categoryValue];
    const targets = appData[apiKey] || [];

    modalTargetSelect.innerHTML = '';
    targets.forEach(t => {
        const option = document.createElement('option');
        option.value = String(t.id); // Ensure string
        option.textContent = categoryValue === 'background' ? t.name : `${t.clan || ''} ${t.name}`.trim();
        modalTargetSelect.appendChild(option);
    });
    updateDestPathPreview();
}

function updateDestPathPreview() {
    const categoryValue = modalCategorySelect.value;
    const targetId = modalTargetSelect.value;
    const apiKey = categoryMap[categoryValue];
    const targets = appData[apiKey] || [];
    const target = targets.find(t => String(t.id) === targetId);

    let path = '';
    if (target) {
        if (categoryValue === 'daimyo') {
            path = `assets/portraits/daimyo/daimyo_${String(targetId).padStart(2, '0')}.png`;
        } else if (categoryValue === 'general') {
            path = `assets/portraits/generals/general_${String(targetId).padStart(2, '0')}.png`;
        } else {
            path = `assets/backgrounds/${target.file}`;
        }
    }
    destPathPreview.textContent = path;
}

function showReflectModal(imgFile, imgData) {
    selectedImageFile = imgFile;
    const modalPromptDisplay = document.getElementById('modal-prompt-display');

    // Display Prompt
    modalPromptDisplay.value = imgData.prompt || "";

    // Strict Priority: Metadata > Fallback to current UI selection
    let initialCategory = imgData.category && imgData.category !== 'unknown' ? imgData.category : categorySelect.value;

    // Set Modal Category
    modalCategorySelect.value = initialCategory;

    // Update Target List
    updateModalTargetList();

    // Determine Target ID
    let targetId = imgData.target_id;
    // Fallback if no target_id in metadata, but ONLY if category matches current UI
    if (!targetId && initialCategory === categorySelect.value) {
        targetId = targetSelect.value;
    }

    // Standardize Target ID string
    const targetIdStr = (targetId !== undefined && targetId !== null) ? String(targetId).trim() : "";

    // Robust Selection Loop
    let found = false;
    // Debug info collector
    let optionsDebug = [];

    for (let i = 0; i < modalTargetSelect.options.length; i++) {
        const opt = modalTargetSelect.options[i];
        optionsDebug.push(`'${opt.value}'`);

        if (opt.value === targetIdStr) {
            modalTargetSelect.selectedIndex = i;
            found = true;
            break;
        }
    }

    if (!found) {
        console.warn(`Target ID '${targetIdStr}' not found in options: [${optionsDebug.join(', ')}]`);
        if (targetIdStr) {
            alert(`Debug: Matching ${targetIdStr} against options...`);
        }
        if (modalTargetSelect.options.length > 0) {
            modalTargetSelect.selectedIndex = 0;
        }
    }

    updateDestPathPreview();

    selectedImagePreview.innerHTML = `<img src="/assets-test/${imgFile}">`;
    selectionOverlay.classList.remove('hidden');
}

modalCategorySelect.onchange = updateModalTargetList;
modalTargetSelect.onchange = updateDestPathPreview;


generateBtn.onclick = async () => {
    const categoryValue = categorySelect.value;
    const targetId = targetSelect.value;
    const apiKey = categoryMap[categoryValue];
    const target = appData[apiKey].find(t => t.id == targetId);
    const targetName = categoryValue === 'background' ? target.name : `${target.clan || ''} ${target.name}`.trim();
    const prompt = promptInput.value;
    const size = categoryValue === 'background' ? '1280x720' : '256x256';

    generateBtn.disabled = true;
    generateBtn.textContent = '生成中...';

    try {
        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: categoryValue,
                target_id: targetId,
                target_name: targetName,
                prompt: prompt,
                size: size
            })
        });

        const result = await res.json();
        if (res.ok) {
            alert("画像生成が完了しました！");
            fetchImages();
        } else {
            alert("エラー: " + result.message);
        }
    } catch (e) {
        alert("エラーが発生しました。");
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = '画像生成（依頼）';
    }
};

confirmReflectBtn.onclick = async () => {
    // Use values from MODAL, not main UI
    const category = modalCategorySelect.value;
    const targetId = modalTargetSelect.value;
    const apiKey = categoryMap[category];
    const target = appData[apiKey].find(t => t.id == targetId);

    const res = await fetch('/api/select-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            file: selectedImageFile,
            type: category,
            id: category === 'background' ? target.file : targetId
        })
    });

    if (res.ok) {
        alert("画像を assets に反映しました。");
        selectionOverlay.classList.add('hidden');
    } else {
        alert("エラーが発生しました。");
    }
};

cancelReflectBtn.onclick = () => {
    selectionOverlay.classList.add('hidden');
};

categorySelect.onchange = updateTargetList;
targetSelect.onchange = updateTargetInfo;

init();
