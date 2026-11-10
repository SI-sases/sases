
window.openSasesExternalApi = async function() {
    let html = `
        <div class="me-menu" style="margin-bottom: 20px;">
            <div class="me-menu-item" onclick="window.openAddApiModal()" style="justify-content: center; color: #007aff;">
                <span style="font-weight: bold;">+ 添加外部 API</span>
            </div>
        </div>
        <div id="external-api-list">
            <div style="text-align: center; color: #999; padding: 20px;">加载中...</div>
        </div>
    `;
    window.openSubpage('🔌 我的外部 API', html);
    window.loadSasesApiList();
};

window.loadSasesApiList = async function() {
    const listDiv = document.getElementById('external-api-list');
    if (!listDiv) return;
    try {
        const token = localStorage.getItem('sases_token');
        const res = await fetch('/api/user-api/list', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await res.json();
        if (!data.apis || data.apis.length === 0) {
            listDiv.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;">暂无配置的 API</div>';
            return;
        }
        let h = '<div class="me-menu">';
        for (let a of data.apis) {
            h += `
                <div class="me-menu-item">
                    <div class="menu-label">
                        <div style="font-size: 15px; color: #333;">${a.api_name}</div>
                        <div style="font-size: 12px; color: #999;">${a.method} ${a.endpoint}</div>
                    </div>
                    <button class="save-btn" style="background: #ff3b30; padding: 4px 8px; font-size: 12px;" onclick="window.deleteSasesApi(${a.id})">删除</button>
                </div>
            `;
        }
        h += '</div>';
        listDiv.innerHTML = h;
    } catch (e) {
        listDiv.innerHTML = '<div style="text-align: center; color: #ff3b30; padding: 20px;">加载失败：' + e.message + '</div>';
    }
};

window.deleteSasesApi = async function(id) {
    if (!confirm('确认删除该 API 吗？')) return;
    const token = localStorage.getItem('sases_token');
    await fetch('/api/user-api/' + id, { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
    window.loadSasesApiList();
};


window.openAddApiModal = function() {
    let html = `
        <div style="padding: 15px;">
            <button class="save-btn" style="background: #888; margin-bottom: 15px; width: 100%;" onclick="window.openSasesExternalApi()">返回列表</button>
            <div style="margin-bottom: 10px;"><input type="text" id="api-name" placeholder="API 名称" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>
            <div style="margin-bottom: 10px;"><input type="text" id="api-endpoint" placeholder="接口URL" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>
            <div style="margin-bottom: 10px;"><input type="text" id="api-desc" placeholder="描述" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>
            <div style="margin-bottom: 10px;"><input type="text" id="api-key" placeholder="API Key (若无鉴权留空)" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>
            <div style="margin-bottom: 10px;"><input type="text" id="api-params" placeholder='参数示例 JSON (如: {"latitude": 39.9})' style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>
            <button class="save-btn" style="width: 100%; padding: 12px; margin-top: 10px;" onclick="window.submitSasesApi()">保存配置</button>
        </div>
    `;
    window.openSubpage('添加外部 API', html, { returnAction: () => window.openSasesExternalApi() });
};

window.submitSasesApi = async function() {
    const name = document.getElementById('api-name').value;
    const endpoint = document.getElementById('api-endpoint').value;
    const desc = document.getElementById('api-desc').value;
    const key = document.getElementById('api-key').value;
    const params = document.getElementById('api-params').value;
    if (!name || !endpoint) { alert('名称和 URL 为必填项'); return; }
    const payload = { api_name: name, endpoint: endpoint, api_desc: desc, auth_key: key, auth_type: key ? 'bearer' : 'none', params_example: params, method: 'GET' };
    try {
        const token = localStorage.getItem('sases_token');
        const res = await fetch('/api/user-api/add', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }, body: JSON.stringify(payload) });
        if (!res.ok) throw new Error('请求失败');
        alert('添加成功！');
        window.openSasesExternalApi();
    } catch (e) { alert('添加失败: ' + e.message); }
}
window.submitSasesApi()">保存配置</button>
        </div>
    `;
    window.openSubpage('添加外部 API', html, { returnAction: () => window.openSasesExternalApi() });
};

window.submitSasesApi = async function() {
    const name = document.getElementById('api-name').value;
    const endpoint = document.getElementById('api-endpoint').value;
    const desc = document.getElementById('api-desc').value;
    if (!name || !endpoint) { alert('名称和 URL 为必填项'); return; }
    const payload = { api_name: name, endpoint: endpoint, api_desc: desc, method: 'GET' };
    
    try {
        const token = localStorage.getItem('sases_token');
        const res = await fetch('/api/user-api/add', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }, body: JSON.stringify(payload) });
        if (!res.ok) throw new Error('请求失败');
        alert('添加成功！');
        window.openSasesExternalApi();
    } catch (e) { alert('添加失败: ' + e.message); }
}
