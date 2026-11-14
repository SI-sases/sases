window.__openExternalApiPage = async function() {
    let html = `
        <div class="me-menu" style="margin-bottom: 20px;">
            <div class="me-menu-item" onclick="window.__openAddApiModal()" style="justify-content: center; color: #007aff;">
                <span style="font-weight: bold;">+ 添加外部 API</span>
            </div>
        </div>
        <div id="external-api-list">
            <div style="text-align: center; color: #999; padding: 20px;">加载中...</div>
        </div>
    `;
    window.openSubpage('🔌 我的外部 API', html);
    loadApiList();
};

async function loadApiList() {
    const listDiv = document.getElementById('external-api-list');
    if (!listDiv) return;
    try {
        const token = localStorage.getItem('sases_token');
        const res = await fetch('/api/user-api/list', { headers: { 'Authorization': 'Bearer ' + token } });
        const data = await res.json();
        if (!data.apis || data.apis.length === 0) {
            listDiv.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;">暂无配置的 API</div>';
            return;
        }
        let html = '<div class="me-menu">';
        for (let a of data.apis) {
            html += `
                <div class="me-menu-item">
                    <div class="menu-label">
                        <div style="font-size: 15px; color: #333;">${a.api_name}</div>
                        <div style="font-size: 12px; color: #999;">${a.method} ${a.endpoint}</div>
                    </div>
                    <button class="save-btn" style="background: #ff3b30; padding: 4px 8px; font-size: 12px;" onclick="window.__deleteApi(${a.id})">删除</button>
                </div>
            `;
        }
        html += '</div>';
        listDiv.innerHTML = html;
    } catch (e) {
        listDiv.innerHTML = '<div style="text-align: center; color: #ff3b30; padding: 20px;">加载失败: ' + e.message + '</div>';
    }
}

window.__deleteApi = async function(id) {
    if (!confirm('确认删除该 API 吗？')) return;
    const token = localStorage.getItem('sases_token');
    await fetch('/api/user-api/' + id, { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
    loadApiList();
};

window.__openAddApiModal = function() {
    let html = `
        <div style="padding: 15px;">
            <input type="text" id="api-name" placeholder="API 名称 (如：ComfyUI出图)" style="width:100%; margin-bottom:10px; padding:8px;">
            <input type="text" id="api-url" placeholder="接口地址 (https://...)" style="width:100%; margin-bottom:10px; padding:8px;">
            <select id="api-method" style="width:100%; margin-bottom:10px; padding:8px;">
                <option value="GET">GET</option>
                <option value="POST">POST</option>
            </select>
            <select id="api-task-mode" style="width:100%; margin-bottom:10px; padding:8px;" onchange="document.getElementById('async-spec-div').style.display = this.value === 'async' ? 'block' : 'none';">
                <option value="sync">同步任务 (直接返回结果)</option>
                <option value="async">异步任务 (需要轮询)</option>
            </select>
            <div id="async-spec-div" style="display:none; margin-bottom:10px;">
                <textarea id="api-async-spec" placeholder='异步规范 JSON (参考异步接入方案):&#10;{&#10;  "submit": {"endpoint": "/gen", "method": "POST", "handle_path": "$.id"},&#10;  "poll": {"endpoint": "/status/{handle}", "done_values": ["done"]}&#10;}' style="width:100%; height:100px; padding:8px; font-family:monospace;"></textarea>
            </div>
            <button class="save-btn" onclick="window.__saveApi()" style="width:100%;">保存</button>
        </div>
    `;
    window.openSubpage('添加外部 API', html, { returnAction: () => window.__openExternalApiPage() });
};

window.__saveApi = async function() {
    const name = document.getElementById('api-name').value;
    const url = document.getElementById('api-url').value;
    const method = document.getElementById('api-method').value;
    const task_mode = document.getElementById('api-task-mode').value;
    const async_spec = document.getElementById('api-async-spec').value;
    
    if(!name || !url) return alert('名称和地址不能为空');
    
    const token = localStorage.getItem('sases_token');
    await fetch('/api/user-api/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ api_name: name, endpoint: url, method: method, task_mode: task_mode, async_spec: async_spec })
    });
    window.__openExternalApiPage();
};

window.__saveApi = async function() {
    const name = document.getElementById('api-name').value;
    const url = document.getElementById('api-url').value;
    const method = document.getElementById('api-method').value;
    if(!name || !url) return alert('名称和地址不能为空');
    const token = localStorage.getItem('sases_token');
    await fetch('/api/user-api/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ api_name: name, endpoint: url, method: method })
    });
    window.__openExternalApiPage();
};