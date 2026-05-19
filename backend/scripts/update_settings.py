import sys
sys.stdout.reconfigure(encoding='utf-8')

filepath = r'c:\Trae\PyCharm_\ai_chat_system\frontend\index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the renderSettingsPanel function
start_marker = '        function renderSettingsPanel() {'
end_marker = '        function updateTemperature(value) {'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print('ERROR: markers not found')
    print('start_idx:', start_idx, 'end_idx:', end_idx)
    sys.exit(1)

new_func = r"""        function renderSettingsPanel() {
            const body = document.getElementById('settingsPanelBody');
            
            let html = `
                <div class="settings-section">
                    <div class="settings-title">🔑 API Key 配置</div>
                    <p style="font-size: 12px; color: #737373; margin-bottom: 16px;">
                        配置各模型的API Key后才能使用对应模型。Key会安全保存在服务器的.env文件中。
                    </p>
                    <div id="apiKeyConfigContainer">
                        <p style="text-align: center; color: #737373; padding: 20px;">加载中...</p>
                    </div>
                </div>
                
                <hr style="border: none; border-top: 1px solid #262626; margin: 20px 0;">
                
                <div class="settings-section">
                    <div class="settings-title">🌡️ 温度 (Temperature)</div>
                    <div class="slider-container">
                        <input type="range" min="0" max="100" value="${chatSettings.temperature * 100}" 
                               oninput="updateTemperature(this.value)">
                        <span class="slider-value">${chatSettings.temperature.toFixed(2)}</span>
                    </div>
                    <p style="font-size: 12px; color: #737373; margin-top: 8px;">
                        控制回复的创造性。值越高越有创意，值越低越保守。
                    </p>
                </div>
                
                <div class="settings-section">
                    <div class="settings-title"> 最大Token数</div>
                    <div class="slider-container">
                        <input type="range" min="500" max="4000" step="100" value="${chatSettings.max_tokens}" 
                               oninput="updateMaxTokens(this.value)">
                        <span class="slider-value">${chatSettings.max_tokens}</span>
                    </div>
                    <p style="font-size: 12px; color: #737373; margin-top: 8px;">
                        限制AI回复的最大长度。
                    </p>
                </div>
                
                <div class="settings-section">
                    <div class="settings-title"> Top P</div>
                    <div class="slider-container">
                        <input type="range" min="0" max="100" value="${chatSettings.top_p * 100}" 
                               oninput="updateTopP(this.value)">
                        <span class="slider-value">${chatSettings.top_p.toFixed(2)}</span>
                    </div>
                    <p style="font-size: 12px; color: #737373; margin-top: 8px;">
                        控制回复的多样性。值越高越多样化。
                    </p>
                </div>
            `;
            
            body.innerHTML = html;
            
            // 加载API Key配置
            loadApiKeyConfig();
        }
        
        async function loadApiKeyConfig() {
            const container = document.getElementById('apiKeyConfigContainer');
            if (!container) return;
            
            try {
                const response = await fetch(`${API_BASE}/api/models/api-keys`);
                const data = await response.json();
                
                if (!data.success || !data.providers) {
                    container.innerHTML = '<p style="color: #f44336;">加载API Key配置失败</p>';
                    return;
                }
                
                let html = '';
                for (const [provider, config] of Object.entries(data.providers)) {
                    const statusIcon = config.configured ? '✅' : '';
                    const statusText = config.configured ? '已配置' : '未配置';
                    const maskedKey = config.masked_key || '';
                    
                    html += `
                        <div class="api-key-item" style="background: #171717; padding: 12px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #262626;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 14px; font-weight: 600; color: #e5e5e5;">${statusIcon} ${provider}</span>
                                <span style="font-size: 12px; color: ${config.configured ? '#4caf50' : '#f44336'};">${statusText}</span>
                            </div>
                            ${maskedKey ? `<p style="font-size: 11px; color: #737373; margin-bottom: 8px;">当前Key: ${maskedKey}</p>` : ''}
                            <div style="display: flex; gap: 8px;">
                                <input type="password" id="apiKey_${provider}" placeholder="输入API Key" 
                                       style="flex: 1; padding: 8px 12px; border: 1px solid #262626; border-radius: 6px; background: #0a0a0a; color: #e5e5e5; font-size: 13px;">
                                <button class="form-btn primary" onclick="saveApiKey('${provider}', '${config.env_name}')" 
                                        style="padding: 8px 16px; white-space: nowrap;">保存</button>
                            </div>
                        </div>
                    `;
                }
                
                container.innerHTML = html;
                
            } catch (error) {
                console.error('加载API Key配置失败:', error);
                container.innerHTML = '<p style="color: #f44336;">加载失败，请检查网络连接</p>';
            }
        }
        
        async function saveApiKey(provider, envName) {
            const input = document.getElementById(`apiKey_${provider}`);
            const apiKey = input.value.trim();
            
            if (!apiKey) {
                alert('请输入API Key');
                return;
            }
            
            const btn = input.nextElementSibling;
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = '保存中...';
            
            try {
                const response = await fetch(`${API_BASE}/api/models/api-keys`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        env_name: envName,
                        api_key: apiKey
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert('✅ API Key保存成功！');
                    input.value = '';
                    // 重新加载配置
                    await loadApiKeyConfig();
                    // 重新加载模型列表
                    await loadModels();
                } else {
                    alert('❌ 保存失败: ' + data.message);
                }
            } catch (error) {
                console.error('保存API Key失败:', error);
                alert(' 保存失败，请检查网络连接');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }
        
"""

# Replace the old function with the new one
new_content = content[:start_idx] + new_func + content[end_idx:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('SUCCESS: Function replaced successfully')
print('New content length:', len(new_content))
