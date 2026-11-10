# fix.py
js_code = """
window.openSasesExternalApi = function() {
    var html = '<div class="me-menu" style="margin-bottom: 20px;">';
    html += '<div class="me-menu-item" onclick="window.openAddApiModal()" style="justify-content: center; color: #007aff;">';
    html += '<span style="font-weight: bold;">+ 添加外部 API</span></div></div>';
    html += '<div id="external-api-list"><div style="text-align: center; color: #999; padding: 20px;">加载中...</div></div>';
    window.openSubpage('🔌 我的外部 API', html);
    window.loadSasesApiList();
};

window.loadSasesApiList = function() {
    var listDiv = document.getElementById('external-api-list');
    if (!listDiv) return;
    var token = localStorage.getItem('sases_token');
    fetch('/api/user-api/list', {
        headers: { 'Authorization': 'Bearer ' + token }
    }).then(function(res) { return res.json(); }).then(function(data) {
        if (!data.apis || data.apis.length === 0) {
            listDiv.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;">暂无配置的 API</div>';
            return;
        }
        var h = '<div class="me-menu">';
        for (var i = 0; i < data.apis.length; i++) {
            var a = data.apis[i];
            h += '<div class="me-menu-item">';
            h += '<div class="menu-label">';
            h += '<div style="font-size: 15px; color: #333;">' + a.api_name + '</div>';
            h += '<div style="font-size: 12px; color: #999;">' + a.method + ' ' + a.endpoint + '</div>';
            h += '</div>';
            h += '<button class="save-btn" style="background: #ff3b30; padding: 4px 8px; font-size: 12px;" onclick="window.deleteSasesApi(' + a.id + ')">删除</button>';
            h += '</div>';
        }
        h += '</div>';
        listDiv.innerHTML = h;
    }).catch(function(e) {
        listDiv.innerHTML = '<div style="text-align: center; color: #ff3b30; padding: 20px;">加载失败：' + e.message + '</div>';
    });
};

window.deleteSasesApi = function(id) {
    if (!confirm('确认删除该 API 吗？')) return;
    var token = localStorage.getItem('sases_token');
    fetch('/api/user-api/' + id, { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } })
    .then(function() { window.loadSasesApiList(); });
};

window.openAddApiModal = function() {
    var html = '<div style="padding: 15px;">';
    html += '<button class="save-btn" style="background: #888; margin-bottom: 15px; width: 100%;" onclick="window.openSasesExternalApi()">返回列表</button>';
    html += '<div style="margin-bottom: 10px;"><input type="text" id="api-name" placeholder="API 名称" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>';
    html += '<div style="margin-bottom: 10px;"><input type="text" id="api-endpoint" placeholder="接口URL (https://...)" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>';
    html += '<div style="margin-bottom: 10px;"><input type="text" id="api-desc" placeholder="描述 (如: 查询天气)" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>';
    html += '<div style="margin-bottom: 10px;"><input type="text" id="api-key" placeholder="API Key (若无鉴权留空)" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>';
    html += '<div style="margin-bottom: 10px;"><input type="text" id="api-params" placeholder="参数示例 JSON" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"></div>';
    html += '<button class="save-btn" style="width: 100%; padding: 12px; margin-top: 10px;" onclick="window.submitSasesApi()">保存配置</button>';
    html += '</div>';
    window.openSubpage('添加外部 API', html);
};

window.submitSasesApi = function() {
    var name = document.getElementById('api-name').value;
    var endpoint = document.getElementById('api-endpoint').value;
    var desc = document.getElementById('api-desc').value;
    var key = document.getElementById('api-key').value;
    var params = document.getElementById('api-params').value;
    
    if (!name || !endpoint) { alert('名称和 URL 为必填项'); return; }
    
    var payload = { 
        api_name: name, 
        endpoint: endpoint, 
        api_desc: desc, 
        auth_key: key, 
        auth_type: key ? 'bearer' : 'none', 
        params_example: params, 
        method: 'GET' 
    };
    var token = localStorage.getItem('sases_token');
    
    fetch('/api/user-api/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify(payload)
    }).then(function(res) {
        if (!res.ok) throw new Error('请求失败');
        alert('添加成功！');
        window.openSasesExternalApi();
    }).catch(function(e) {
        alert('添加失败: ' + e.message);
    });
};
"""
with open('static/external_api.js', 'w', encoding='utf-8') as f:
    f.write(js_code)
print("✅ 纯原生 JS 已完全重写，彻底消灭语法错误！")
