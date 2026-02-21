const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const questionInput = document.getElementById('questionInput');
const sendButton = document.getElementById('sendButton');
const chatContainer = document.getElementById('chatContainer');
const modal = document.getElementById('modal');
const modalTitle = document.getElementById('modalTitle');
const modalText = document.getElementById('modalText');
const closeBtn = document.querySelector('.close');
const clearButton = document.getElementById('clearButton');
const refreshButton = document.getElementById('refreshButton');
const filesList = document.getElementById('filesList');

let isUploaded = false;

async function loadFiles() {
    try {
        const response = await fetch('/files');
        const data = await response.json();
        renderFilesList(data.files);
    } catch (error) {
        console.error('加载文件列表失败:', error);
    }
}

function renderFilesList(files) {
    if (files.length === 0) {
        filesList.innerHTML = '<div class="empty-files"><p>暂无上传的文件</p></div>';
        return;
    }
    
    filesList.innerHTML = files.map(file => `
        <div class="file-item">
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-meta">${file.chunks} 个文档块 · ${file.upload_time}</div>
            </div>
            <div class="file-actions">
                <button class="delete-file-button" data-filename="${file.filename}" title="删除文件">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6"></path>
                    </svg>
                    删除
                </button>
            </div>
        </div>
    `).join('');
    
    document.querySelectorAll('.delete-file-button').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const filename = btn.dataset.filename;
            await deleteFile(filename);
        });
    });
}

async function deleteFile(filename) {
    if (confirm(`确定要删除文件 "${filename}" 吗？`)) {
        try {
            const response = await fetch(`/files/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                const data = await response.json();
                alert(data.message);
                await loadFiles();
            } else {
                const errorData = await response.json();
                alert(errorData.detail || '删除失败');
            }
        } catch (error) {
            alert('网络错误，请重试');
        }
    }
}

uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

async function handleFile(file) {
    if (!file.name.endsWith('.pdf')) {
        showStatus('error', '仅支持PDF文件');
        return;
    }

    showStatus('processing', '正在解析PDF...');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showStatus('success', data.message);
            isUploaded = true;
            questionInput.disabled = false;
            sendButton.disabled = false;
            chatContainer.innerHTML = '';
            addMessage('assistant', '文件已成功处理！现在您可以开始提问了。');
            await loadFiles();
        } else {
            showStatus('error', data.detail || '上传失败');
        }
    } catch (error) {
        showStatus('error', '网络错误，请重试');
    }
}

function showStatus(type, message) {
    uploadStatus.className = `upload-status ${type}`;
    uploadStatus.textContent = message;
}

sendButton.addEventListener('click', sendMessage);

questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

async function sendMessage() {
    const question = questionInput.value.trim();
    if (!question) return;

    addMessage('user', question);
    questionInput.value = '';

    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message assistant';
    thinkingDiv.innerHTML = '<div class="message-content thinking">正在思考...</div>';
    chatContainer.appendChild(thinkingDiv);
    scrollToBottom();

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        if (!response.ok) {
            throw new Error('请求失败');
        }

        chatContainer.removeChild(thinkingDiv);

        const answerDiv = document.createElement('div');
        answerDiv.className = 'message assistant';
        answerDiv.innerHTML = '<div class="message-content"></div>';
        chatContainer.appendChild(answerDiv);

        const contentDiv = answerDiv.querySelector('.message-content');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;
            contentDiv.innerHTML = marked.parse(fullText);
            scrollToBottom();
        }

        addCitationListeners();

    } catch (error) {
        if (chatContainer.contains(thinkingDiv)) {
            thinkingDiv.querySelector('.message-content').textContent = '抱歉，发生错误，请重试。';
        }
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${marked.parse(content)}</div>`;
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function addCitationListeners() {
    const citations = document.querySelectorAll('.citation');
    citations.forEach(citation => {
        citation.addEventListener('click', (e) => {
            e.preventDefault();
            const source = citation.textContent;
            showModal(source);
        });
    });
}

function showModal(text) {
    modalTitle.textContent = '文献片段';
    modalText.textContent = text;
    modal.style.display = 'block';
}

closeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
});

clearButton.addEventListener('click', async () => {
    if (confirm('确定要清除所有上传的PDF文件和向量数据库吗？此操作不可恢复。')) {
        try {
            const response = await fetch('/clear', {
                method: 'DELETE'
            });

            if (response.ok) {
                const data = await response.json();
                alert(data.message);
                isUploaded = false;
                questionInput.disabled = true;
                sendButton.disabled = true;
                chatContainer.innerHTML = `
                    <div class="welcome-message">
                        <p>欢迎使用学术论文问答系统！</p>
                        <p>请先上传PDF论文，然后开始提问。</p>
                    </div>
                `;
            } else {
                alert('清除失败，请重试');
            }
        } catch (error) {
            alert('网络错误，请重试');
        }
    }
});

refreshButton.addEventListener('click', loadFiles);

window.addEventListener('DOMContentLoaded', () => {
    loadFiles();
});

window.addEventListener('click', (e) => {
    if (e.target === modal) {
        modal.style.display = 'none';
    }
});
