// 全局变量
let allPrompts = [];
let filteredPrompts = [];
let currentConversationId = null;
let isProcessing = false;
let isMultiTurnEnabled = false; // 是否启用多轮对话
let lastUsedPromptId = null; // 最近一次使用的prompt ID

// 历史对话相关变量
let conversations = [];
let currentConversation = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化UI
    initUI();
    
    // 加载提示词列表
    loadPrompts();
    
    // 加载历史对话
    loadConversations();
    
    // 绑定事件
    bindEvents();
});

// 初始化UI元素
function initUI() {
    // 创建对话区域
    const chatArea = document.querySelector('.flex-1.overflow-y-auto.p-4 .flex.flex-col.gap-6');
    if (chatArea) {
        chatArea.innerHTML = `
            <div class="text-center text-gray-400 my-8">
                <div class="mb-4">
                    <img src="/static/LOGO1.jpg" alt="LOGO" class="w-16 h-16 rounded-full mx-auto object-cover">
                </div>
                <div class="text-xl font-medium">我是Mobo，有什么可以帮忙的？</div>
                <div class="mt-2"></div>
            </div>
        `;
    }
    
    // 初始化搜索框
    const searchInput = document.querySelector('.search-container input');
    if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
    }
    
    // 初始化侧边栏（默认收起）
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.style.display = 'none';
        
        // 展开主内容区域
        const mainContent = document.querySelector('.flex-1.flex.flex-col');
        if (mainContent) {
            mainContent.style.marginLeft = '0';
            mainContent.style.width = '100%';
        }
    }
    
    // 更新侧边栏内容
    updateSidebar();
}

// 加载历史对话
function loadConversations() {
    // 尝试从localStorage加载历史对话
    const savedConversations = localStorage.getItem('expert_conversations');
    if (savedConversations) {
        try {
            conversations = JSON.parse(savedConversations);
            
            // 如果有对话历史，获取最近一次使用的promptId
            if (conversations.length > 0 && conversations[0].lastUsedPromptId) {
                lastUsedPromptId = conversations[0].lastUsedPromptId;
                console.log(`从历史对话中恢复lastUsedPromptId: ${lastUsedPromptId}`);
            }
            
            updateSidebar();
        } catch (e) {
            console.error('解析历史对话失败:', e);
            conversations = [];
        }
    }
}

// 保存历史对话到localStorage
function saveConversations() {
    try {
        localStorage.setItem('expert_conversations', JSON.stringify(conversations));
    } catch (e) {
        console.error('保存历史对话失败:', e);
    }
}

// 创建新对话
function createNewConversation() {
    // 清空当前的对话内容
    const chatArea = document.querySelector('.flex-1.overflow-y-auto.p-4 .flex.flex-col.gap-6');
    if (chatArea) {
        chatArea.innerHTML = `
            <div class="text-center text-gray-400 my-8">
                <div class="mb-4">
                    <img src="/static/LOGO1.jpg" alt="LOGO" class="w-16 h-16 rounded-full mx-auto object-cover">
                </div>
                <div class="text-xl font-medium">专家模式已就绪</div>
                <div class="mt-2">从右侧选择一个提示词开始分析</div>
            </div>
        `;
    }
    
    // 创建新的对话对象
    currentConversation = {
        id: Date.now().toString(),
        title: '新对话',
        timestamp: new Date().toISOString(),
        messages: [],
        lastUsedPromptId: null
    };
    
    // 添加到对话列表
    conversations.unshift(currentConversation);
    
    // 限制最多保存50个对话
    if (conversations.length > 50) {
        conversations = conversations.slice(0, 50);
    }
    
    // 更新侧边栏
    updateSidebar();
    
    // 保存到localStorage
    saveConversations();
}

// 选择历史对话
function selectConversation(conversationId) {
    const conversation = conversations.find(c => c.id === conversationId);
    if (!conversation) return;
    
    // 更新当前对话
    currentConversation = conversation;
    
    // 恢复该对话的lastUsedPromptId
    if (conversation.lastUsedPromptId) {
        lastUsedPromptId = conversation.lastUsedPromptId;
        console.log(`从选择的对话中恢复lastUsedPromptId: ${lastUsedPromptId}`);
    }
    
    // 清空并重建对话内容
    const chatArea = document.querySelector('.flex-1.overflow-y-auto.p-4 .flex.flex-col.gap-6');
    if (chatArea) {
        chatArea.innerHTML = '';
        
        // 重建所有消息
        conversation.messages.forEach(msg => {
            if (msg.role === 'user') {
                // 添加用户消息
                addUserMessage(msg.content, false);
            } else if (msg.role === 'ai') {
                // 添加AI消息
                addAIMessage(msg.content);
            }
        });
        
        // 如果没有消息，显示欢迎信息
        if (conversation.messages.length === 0) {
            chatArea.innerHTML = `
                <div class="text-center text-gray-400 my-8">
                    <div class="mb-4">
                        <img src="/static/LOGO1.jpg" alt="LOGO" class="w-16 h-16 rounded-full mx-auto object-cover">
                    </div>
                    <div class="text-xl font-medium">专家模式已就绪</div>
                    <div class="mt-2">从右侧选择一个提示词开始分析</div>
                </div>
            `;
        }
    }
    
    // 高亮当前选择的对话
    updateSidebar();
}

// 更新侧边栏的历史对话列表
function updateSidebar() {
    const sidebarContent = document.querySelector('#sidebar .flex-1.overflow-y-auto');
    if (!sidebarContent) return;
    
    // 清空内容
    sidebarContent.innerHTML = '';
    
    // 如果没有对话历史，显示空状态
    if (conversations.length === 0) {
        sidebarContent.innerHTML = `
            <div class="p-4 text-center text-gray-400">
                <i class="fas fa-comment-slash mb-2 text-2xl"></i>
                <p>暂无历史对话</p>
                <button class="mt-4 text-xs bg-[#404040] hover:bg-[#505050] px-3 py-1.5 !rounded-button new-conversation">
                    开始新对话
                </button>
            </div>
        `;
        
        // 绑定新对话按钮
        const newConversationBtn = sidebarContent.querySelector('.new-conversation');
        if (newConversationBtn) {
            newConversationBtn.addEventListener('click', createNewConversation);
        }
        
        return;
    }
    
    // 添加所有对话历史
    conversations.forEach(conversation => {
        const isActive = currentConversation && conversation.id === currentConversation.id;
        const date = new Date(conversation.timestamp);
        const formattedDate = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
        
        // 获取最后一条消息作为预览
        let previewText = '暂无消息';
        if (conversation.messages && conversation.messages.length > 0) {
            const lastMessage = conversation.messages[conversation.messages.length - 1];
            previewText = lastMessage.content;
            if (previewText.length > 50) {
                previewText = previewText.substring(0, 50) + '...';
            }
        }
        
        const conversationElement = document.createElement('div');
        conversationElement.className = `${isActive ? 'bg-[#2A2A2A]' : 'hover:bg-[#2A2A2A]'} p-4 cursor-pointer border-b border-gray-700 conversation-item`;
        conversationElement.dataset.id = conversation.id;
        conversationElement.innerHTML = `
            <div class="text-sm font-medium">${conversation.title || '无标题对话'}</div>
            <div class="text-xs text-gray-400 mt-1">${formattedDate}</div>
            <div class="text-xs text-gray-400 mt-2 line-clamp-2">${previewText}</div>
        `;
        sidebarContent.appendChild(conversationElement);
    });
    
    // 绑定对话选择事件
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.addEventListener('click', () => {
            const conversationId = item.dataset.id;
            selectConversation(conversationId);
        });
    });
}

// 加载提示词列表
async function loadPrompts() {
    try {
        const response = await fetch('/mobo/prompt.json');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        allPrompts = await response.json();
        
        // 按ID排序
        allPrompts.sort((a, b) => a.id - b.id);
        
        // 初始显示所有提示词
        filteredPrompts = [...allPrompts];
        
        // 渲染提示词列表
        renderPromptList(filteredPrompts);
    } catch (error) {
        console.error('加载提示词失败:', error);
        showStatusMessage('加载提示词失败，请刷新页面重试', 'error');
    }
}

// 渲染提示词列表
function renderPromptList(prompts) {
    const promptContainer = document.querySelector('#promptPanel .flex-1.overflow-y-auto');
    if (!promptContainer) return;
    
    // 清空容器
    promptContainer.innerHTML = '';
    
    // 如果没有提示词，显示空状态
    if (prompts.length === 0) {
        promptContainer.innerHTML = `
            <div class="p-4 text-center text-gray-400">
                <i class="fas fa-search mb-2 text-2xl"></i>
                <p>未找到匹配的提示词</p>
            </div>
        `;
        return;
    }
    
    // 添加提示词
    prompts.forEach(prompt => {
        const promptElement = document.createElement('div');
        promptElement.className = 'p-4 hover:bg-[#2A2A2A] cursor-pointer border-b border-gray-700';
        
        // 构建提示词详情内容，包括Context和Exception
        let detailsHTML = '';
        
        // 添加Action详情
        if (prompt.Action) {
            detailsHTML += `<p class="text-xs text-gray-400 mt-1 break-words"><span class="text-gray-300">Action:</span> ${prompt.Action}</p>`;
        }
        
        // 添加Context详情
        if (prompt.Context) {
            detailsHTML += `<p class="text-xs text-gray-400 mt-1 break-words"><span class="text-gray-300">Context:</span> ${prompt.Context}</p>`;
        }
        
        // 添加Exception详情
        if (prompt.Exception) {
            detailsHTML += `<p class="text-xs text-gray-400 mt-1 break-words"><span class="text-gray-300">Exception:</span> ${prompt.Exception}</p>`;
        }
        
        promptElement.innerHTML = `
            <div class="text-sm font-medium mb-2">${prompt.Role || '未命名提示词'}</div>
            ${detailsHTML}
            <button class="mt-2 text-xs bg-[#404040] hover:bg-[#505050] px-3 py-1.5 !rounded-button use-prompt" data-id="${prompt.id}">
                <i class="fas fa-copy mr-1"></i>使用
            </button>
        `;
        promptContainer.appendChild(promptElement);
    });
    
    // 绑定使用按钮事件
    document.querySelectorAll('.use-prompt').forEach(button => {
        button.addEventListener('click', (e) => {
            const promptId = parseInt(e.currentTarget.getAttribute('data-id'));
            usePrompt(promptId);
        });
    });
}

// 绑定事件处理
function bindEvents() {
    // 绑定搜索框事件
    const searchInput = document.querySelector('.search-container input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.trim().toLowerCase();
            filterPrompts(searchTerm);
        });
    }
    
    // 绑定新对话按钮
    const newChatButton = document.getElementById('newChatButton');
    if (newChatButton) {
        newChatButton.addEventListener('click', createNewConversation);
    }
    
    // 绑定发送消息按钮
    const sendButton = document.querySelector('.absolute.right-4.bottom-4');
    if (sendButton) {
        sendButton.addEventListener('click', function() {
            const textArea = document.querySelector('textarea');
            if (textArea && textArea.value.trim()) {
                const message = textArea.value.trim();
                textArea.value = '';
                textArea.style.height = 'auto';
                
                if (isMultiTurnEnabled && lastUsedPromptId) {
                    // 多轮对话模式
                    sendMultiTurnMessage(message, lastUsedPromptId);
                } else {
                    // 普通模式
                    sendMessage(message);
                }
            }
        });
    }
    
    // 绑定输入框回车发送
    const textArea = document.querySelector('textarea');
    if (textArea) {
        textArea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const sendButton = document.querySelector('.absolute.right-4.bottom-4');
                if (sendButton) {
                    sendButton.click();
                }
            }
        });
    }
    
    // 绑定多轮对话按钮
    const multiTurnButton = document.getElementById('multiTurnChatButton');
    if (multiTurnButton) {
        multiTurnButton.addEventListener('click', toggleMultiTurnChat);
    }
}

// 切换多轮对话模式
function toggleMultiTurnChat() {
    isMultiTurnEnabled = !isMultiTurnEnabled;
    const multiTurnButton = document.getElementById('multiTurnChatButton');
    const multiTurnStatus = document.getElementById('multiTurnStatus');
    
    // 添加调试输出，检查lastUsedPromptId
    console.log(`切换多轮对话，当前lastUsedPromptId: ${lastUsedPromptId}`);
    console.log(`isMultiTurnEnabled: ${isMultiTurnEnabled}`);
    
    if (isMultiTurnEnabled) {
        // 检查是否有最近使用的prompt ID
        if (!lastUsedPromptId) {
            showStatusMessage('请先使用一个提示词进行分析，然后再开启多轮对话', 'warning');
            isMultiTurnEnabled = false;
            return;
        }
        
        // 更新UI状态
        multiTurnButton.classList.add('bg-green-700');
        multiTurnButton.classList.remove('bg-[#404040]');
        multiTurnStatus.classList.remove('hidden');
        showStatusMessage('多轮对话已开启，使用的是ID为 ' + lastUsedPromptId + ' 的提示词', 'success');
    } else {
        // 更新UI状态
        multiTurnButton.classList.remove('bg-green-700');
        multiTurnButton.classList.add('bg-[#404040]');
        multiTurnStatus.classList.add('hidden');
        showStatusMessage('多轮对话已关闭', 'info');
    }
}

// 发送多轮对话消息
async function sendMultiTurnMessage(message, promptId) {
    try {
        // 添加用户消息
        addUserMessage(message, true);
        
        // 更新当前对话的lastUsedPromptId
        if (currentConversation) {
            currentConversation.lastUsedPromptId = promptId;
            saveConversations();
        }
        
        // 添加思考中提示
        const processingMessageId = addProcessingMessage('正在处理...');
        
        console.log(`发送多轮对话请求: promptId=${promptId}, message=${message}`);
        
        // 发送请求
        const response = await fetch('/expert_api/multi_turn_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                prompt_id: promptId
            })
        });
        
        if (!response.ok) {
            throw new Error('网络请求失败');
        }
        
        const result = await response.json();
        
        // 移除处理中提示
        removeProcessingMessage(processingMessageId);
        
        if (result.success) {
            // 添加AI回复
            addAIMessage(result.response);
            
            // 保存对话记录
            if (currentConversation) {
                currentConversation.messages.push({
                    role: 'ai',
                    content: result.response
                });
                
                // 如果是第一条消息，更新对话标题
                if (currentConversation.messages.length === 2) {
                    currentConversation.title = message.length > 20 ? message.substring(0, 20) + '...' : message;
                    updateSidebar();
                }
                
                saveConversations();
            }
        } else {
            // 添加错误提示
            addAIMessage(`处理失败: ${result.message}`);
        }
    } catch (error) {
        console.error('多轮对话处理出错:', error);
        showStatusMessage('处理失败: ' + error.message, 'error');
    }
}

// 过滤提示词
function filterPrompts(searchTerm) {
    if (!searchTerm) {
        filteredPrompts = [...allPrompts];
    } else {
        filteredPrompts = allPrompts.filter(prompt => {
            const role = (prompt.Role || '').toLowerCase();
            const action = (prompt.Action || '').toLowerCase();
            const context = (prompt.Context || '').toLowerCase();
            
            return role.includes(searchTerm) || 
                   action.includes(searchTerm) || 
                   context.includes(searchTerm);
        });
    }
    
    renderPromptList(filteredPrompts);
}

// 使用提示词
async function usePrompt(promptId) {
    try {
        // 查找提示词
        const prompt = allPrompts.find(p => p.id === promptId);
        if (!prompt) {
            showStatusMessage('未找到提示词', 'error');
            return;
        }
        
        // 记录最后使用的提示词ID
        lastUsedPromptId = promptId;
        
        // 确保有当前对话，如果没有则创建一个
        if (!currentConversation) {
            createNewConversation();
        }
        
        // 更新当前对话的lastUsedPromptId
        currentConversation.lastUsedPromptId = promptId;
        
        // 内容显示
        const promptSummary = `### 分析提示：${prompt.Task || ''}`;
        
        // 添加用户消息和AI思考状态
        addUserMessage(promptSummary, true);
        
        // 更新对话标题为提示词名称
        if (currentConversation.messages.length === 0) {
            currentConversation.title = prompt.Role || '无标题对话';
            saveConversations();
            updateSidebar();
        }
        
        // 在聊天区域添加用户消息
        const userMessage = `Role:${prompt.Role} - Action:${prompt.Action}-Context:${prompt.Context}-Exception:${prompt.Exception}`;
        addUserMessage(userMessage, true);
        
        // 将用户消息添加到当前对话
        currentConversation.messages.push({
            role: 'user',
            content: userMessage,
            timestamp: new Date().toISOString()
        });
        saveConversations();
        
        // 清空输入框
        const textarea = document.querySelector('textarea');
        if (textarea) {
            textarea.value = '';
        }
        
        // 添加AI思考中状态
        const thinkingMessageId = addThinkingMessage();
        
        // 使用SSE连接实时显示处理过程
        let logs = [];
        // 添加时间戳防止缓存
        const timestamp = new Date().getTime();
        const sse_url = `/expert_api/analyze_stream?prompt_id=${promptId}&t=${timestamp}`;
        console.log(`创建SSE连接: ${sse_url}`);
        
        // 创建EventSource连接
        let eventSource = new EventSource(sse_url);
        
        // 创建处理中消息元素
        const processingMessageId = addProcessingMessage('正在初始化分析...');
        
        // 监听事件
        eventSource.onmessage = (event) => {
            try {
                console.log("收到SSE消息:", event.data.substring(0, 100) + "...");
                const data = JSON.parse(event.data);
                
                if (data.type === 'start') {
                    updateProcessingMessage(processingMessageId, '开始分析数据...');
                } 
                else if (data.type === 'log') {
                    // 将新日志添加到日志数组
                    if (Array.isArray(data.logs) && data.logs.length > 0) {
                        logs = logs.concat(data.logs);
                        // 更新处理中消息
                        updateProcessingMessage(processingMessageId, formatLogs(logs));
                    }
                }
                else if (data.type === 'ping') {
                    // 心跳消息，不需要处理
                    console.log("收到心跳消息");
                }
                else if (data.type === 'complete') {
                    // 处理完成，关闭连接
                    console.log("处理完成，结果:", data);
                    eventSource.close();
                    
                    // 移除思考中状态
                    removeThinkingMessage(thinkingMessageId);
                    
                    // 移除处理中消息
                    removeProcessingMessage(processingMessageId);
                    
                    if (data.success) {
                        // 处理结果，显示在AI消息中
                        let resultText = '';
                        
                        // 优先查找报告内容
                        if (data.result && data.result.report_content) {
                            resultText = data.result.report_content;
                            console.log("显示报告文件内容");
                        }
                        // 其次查找响应内容
                        else if (data.result && data.result.response) {
                            resultText = data.result.response;
                            console.log("显示响应内容");
                        } 
                        // 再次查找原始结果中的报告内容
                        else if (data.result && data.result.raw_result && data.result.raw_result.report_content) {
                            resultText = data.result.raw_result.report_content;
                            console.log("显示原始结果中的报告内容");
                        }
                        // 再次查找原始结果中的响应
                        else if (data.result && data.result.raw_result && data.result.raw_result.response) {
                            resultText = data.result.raw_result.response;
                            console.log("显示原始结果中的响应");
                        } 
                        // 查找直接作为字符串的结果
                        else if (typeof data.result === 'string') {
                            resultText = data.result;
                            console.log("显示字符串结果");
                        } 
                        // 尝试JSON序列化结果作为后备
                        else {
                            try {
                                resultText = '未找到有效的分析结果。原始数据:\n\n```json\n' + 
                                            JSON.stringify(data.result, null, 2) + 
                                            '\n```';
                                console.log("显示JSON序列化结果");
                            } catch (e) {
                                resultText = '无法显示结果数据';
                                console.error("序列化结果失败:", e);
                            }
                        }
                        
                        console.log("最终输出结果类型:", typeof resultText);
                        console.log("最终输出结果长度:", resultText ? resultText.length : 0);
                        // 只显示输出的前100个字符，避免日志过长
                        if (resultText && resultText.length > 100) {
                            console.log("最终输出结果前100字符:", resultText.substring(0, 100) + "...");
                        } else {
                            console.log("最终输出结果:", resultText);
                        }
                        
                        const logsText = formatLogs(logs);
                        
                        // 检查结果是否为Markdown格式，如果不是则添加格式化
                        if (resultText && !resultText.includes('#') && !resultText.includes('```')) {
                            // 结果看起来不像Markdown，添加基本格式
                            resultText = `## 分析结果\n\n${resultText}`;
                        }
                        
                        // 如果日志很长，但结果较短，直接将结果放在前面
                        let aiContent = '';
                        if (logsText.length > 1000 && resultText.length < 5000) {
                            aiContent = `${resultText}\n\n### 处理过程：\n\`\`\`\n${logsText}\n\`\`\``;
                        } else {
                            aiContent = `### 处理过程：\n\`\`\`\n${logsText}\n\`\`\`\n\n${resultText}`;
                        }
                        
                        addAIMessage(aiContent);
                        
                        // 记录最后使用的promptId，用于多轮对话
                        lastUsedPromptId = promptId;
                        console.log(`成功记录lastUsedPromptId: ${promptId}`);
                        
                        // 将AI回复添加到当前对话
                        currentConversation.messages.push({
                            role: 'ai',
                            content: aiContent,
                            timestamp: new Date().toISOString()
                        });
                        
                        // 确保当前对话的lastUsedPromptId被更新
                        currentConversation.lastUsedPromptId = promptId;
                        
                        saveConversations();
                        updateSidebar();
                        
                        showStatusMessage('分析完成', 'success');
                    } else {
                        // 处理失败
                        const errorMessage = data.result && data.result.message ? data.result.message : '未知错误';
                        const aiContent = `处理失败: ${errorMessage}`;
                        addAIMessage(aiContent);
                        
                        // 将错误消息添加到当前对话
                        currentConversation.messages.push({
                            role: 'ai',
                            content: aiContent,
                            timestamp: new Date().toISOString()
                        });
                        
                        // 确保当前对话的lastUsedPromptId被更新
                        currentConversation.lastUsedPromptId = promptId;
                        
                        saveConversations();
                        updateSidebar();
                        
                        showStatusMessage(`处理失败: ${errorMessage}`, 'error');
                    }
                    
                    isProcessing = false;
                }
            } catch (e) {
                console.error('处理SSE消息出错:', e, "原始数据:", event.data);
            }
        };
        
        // 处理错误
        eventSource.onerror = (error) => {
            console.error('SSE连接错误:', error);
            
            // 尝试重新连接
            let reconnectAttempts = 0;
            const maxReconnectAttempts = 3;
            
            const reconnect = () => {
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    console.log(`尝试重新连接 (${reconnectAttempts}/${maxReconnectAttempts})...`);
                    
                    // 等待一段时间后重试
                    setTimeout(() => {
                        // 使用新的时间戳创建新连接
                        const newTimestamp = new Date().getTime();
                        const newSseUrl = `/expert_api/analyze_stream?prompt_id=${promptId}&t=${newTimestamp}&retry=${reconnectAttempts}`;
                        
                        console.log(`重新创建SSE连接: ${newSseUrl}`);
                        eventSource.close();
                        const newEventSource = new EventSource(newSseUrl);
                        
                        // 将新的事件处理器复制到新连接
                        newEventSource.onmessage = eventSource.onmessage;
                        newEventSource.onerror = eventSource.onerror;
                        
                        // 更新引用
                        eventSource = newEventSource;
                    }, 1000 * reconnectAttempts); // 递增等待时间
                    
                    return;
                }
                
                // 达到最大重试次数后放弃
                eventSource.close();
                
                // 移除处理中消息
                removeProcessingMessage(processingMessageId);
                
                // 显示错误消息
                const errorContent = '连接中断，请重试';
                addAIMessage(errorContent);
                
                // 将错误消息添加到当前对话
                currentConversation.messages.push({
                    role: 'ai',
                    content: errorContent,
                    timestamp: new Date().toISOString()
                });
                
                // 确保当前对话的lastUsedPromptId被更新
                currentConversation.lastUsedPromptId = promptId;
                
                saveConversations();
                updateSidebar();
                
                showStatusMessage('连接中断，请重试', 'error');
                
                isProcessing = false;
            };
            
            reconnect();
        };
        
    } catch (error) {
        console.error('处理提示词出错:', error);
        removeThinkingMessage();
        const errorContent = `处理失败: ${error.message}`;
        addAIMessage(errorContent);
        
        // 将错误消息添加到当前对话
        if (currentConversation) {
            currentConversation.messages.push({
                role: 'ai',
                content: errorContent,
                timestamp: new Date().toISOString()
            });
            saveConversations();
            updateSidebar();
        }
        
        showStatusMessage(`处理失败: ${error.message}`, 'error');
        isProcessing = false;
    }
}

// 格式化日志
function formatLogs(logs) {
    if (!logs || !logs.length) return "等待处理...";
    
    // 合并日志并清理多余换行
    const mergedLog = logs.join('').replace(/\n{3,}/g, '\n\n');
    
    // 保留最后10000个字符，避免过长
    const maxLength = 10000;
    let result = mergedLog;
    
    if (result.length > maxLength) {
        // 保留最后的部分，并在开头添加提示
        result = "... [日志太长，仅显示最新部分] ...\n\n" + result.substring(result.length - maxLength);
    }
    
    return result;
}

// 发送用户消息
async function sendMessage(message) {
    if (isProcessing) {
        showStatusMessage('正在处理中，请稍候...', 'processing');
        return;
    }
    
    // 确保有当前对话，如果没有则创建一个
    if (!currentConversation) {
        createNewConversation();
    }
    
    // 添加用户消息到聊天区域
    addUserMessage(message, true);
    
    // 将用户消息添加到当前对话
    currentConversation.messages.push({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
    });
    saveConversations();
    
    // 清空输入框
    const textarea = document.querySelector('textarea');
    if (textarea) {
        textarea.value = '';
    }
    
    // 添加AI思考中状态
    const thinkingMessageId = addThinkingMessage();
    
    try {
        isProcessing = true;
        showStatusMessage('正在根据您的需求生成专业分析提示词...', 'processing');
        
        // 调用API自动生成提示词
        console.log('正在发送自动生成提示词请求:', message);
        
        const response = await fetch('/expert_api/auto_generate_prompt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                action: message
            })
        });
        
        console.log('收到API响应状态:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API错误响应:', errorText);
            throw new Error(`生成提示词请求失败: ${response.status} - ${errorText}`);
        }
        
        const resultText = await response.text();
        console.log('API响应内容:', resultText);
        
        let result;
        try {
            result = JSON.parse(resultText);
        } catch (jsonError) {
            console.error('解析JSON响应失败:', jsonError);
            throw new Error(`解析响应失败: ${jsonError.message}，原始响应: ${resultText.substring(0, 100)}...`);
        }
        
        if (!result.success) {
            throw new Error(`生成提示词失败: ${result.message}`);
        }
        
        // 获取自动生成的提示词
        const generatedPrompt = result.prompt;
        console.log('自动生成的提示词:', generatedPrompt);
        
        // 显示一条消息，表示正在处理
        removeThinkingMessage(thinkingMessageId);
        const processingMessageId = addProcessingMessage(`正在使用自动生成的专业提示词进行分析...\n\n角色: ${generatedPrompt.Role}\n\n动作: ${generatedPrompt.Action}\n\n上下文: ${generatedPrompt.Context}\n\n异常情况: ${generatedPrompt.Exception}`);
        
        // 使用生成的提示词ID调用分析流程
        await usePromptWithId(generatedPrompt.id, processingMessageId);
        
        // 分析已完成
        console.log('分析已完成');
        
    } catch (error) {
        console.error('处理消息出错:', error);
        removeThinkingMessage(thinkingMessageId);
        
        const errorContent = `处理失败: ${error.message}`;
        addAIMessage(errorContent);
        
        // 将错误消息添加到当前对话
        if (currentConversation) {
            currentConversation.messages.push({
                role: 'ai',
                content: errorContent,
                timestamp: new Date().toISOString()
            });
            saveConversations();
            updateSidebar();
        }
        
        showStatusMessage(`处理失败: ${error.message}`, 'error');
    } finally {
        isProcessing = false;
    }
}

// 使用指定ID的提示词进行分析
async function usePromptWithId(promptId, processingMessageId = null) {
    if (isProcessing && !processingMessageId) {
        showStatusMessage('正在处理中，请稍候...', 'processing');
        return;
    }
    
    // 立即记录最后使用的promptId，用于多轮对话
    lastUsedPromptId = promptId;
    console.log(`在usePromptWithId开始时设置lastUsedPromptId: ${promptId}`);
    
    // 更新当前对话的lastUsedPromptId
    if (currentConversation) {
        currentConversation.lastUsedPromptId = promptId;
        saveConversations();
    }
    
    try {
        if (!processingMessageId) {
            isProcessing = true;
        }
        
        // 显示正在处理的状态
        showStatusMessage('正在分析数据，请稍候...', 'processing');
        
        // 找到对应的提示词
        const promptResponse = await fetch(`/expert_api/prompt/${promptId}`);
        if (!promptResponse.ok) {
            throw new Error(`获取提示词失败: ${promptResponse.status}`);
        }
        
        const selectedPrompt = await promptResponse.json();
        
        // 使用SSE连接实时显示处理过程
        let logs = [];
        // 添加时间戳防止缓存
        const timestamp = new Date().getTime();
        const sse_url = `/expert_api/analyze_stream?prompt_id=${promptId}&t=${timestamp}`;
        console.log(`创建SSE连接: ${sse_url}`);
        
        // 创建EventSource连接
        let eventSource = new EventSource(sse_url);
        
        // 如果没有传入处理消息ID，创建一个新的
        if (!processingMessageId) {
            processingMessageId = addProcessingMessage('正在初始化分析...');
        }
        
        // 监听事件
        eventSource.onmessage = (event) => {
            try {
                console.log("收到SSE消息:", event.data.substring(0, 100) + "...");
                const data = JSON.parse(event.data);
                
                if (data.type === 'start') {
                    updateProcessingMessage(processingMessageId, '开始分析数据...');
                } 
                else if (data.type === 'log') {
                    // 将新日志添加到日志数组
                    if (Array.isArray(data.logs) && data.logs.length > 0) {
                        logs = logs.concat(data.logs);
                        // 更新处理中消息
                        updateProcessingMessage(processingMessageId, formatLogs(logs));
                    }
                }
                else if (data.type === 'ping') {
                    // 心跳消息，不需要处理
                    console.log("收到心跳消息");
                }
                else if (data.type === 'complete') {
                    // 处理完成，关闭连接
                    console.log("处理完成，结果:", data);
                    eventSource.close();
                    
                    // 移除处理中消息
                    removeProcessingMessage(processingMessageId);
                    
                    if (data.success) {
                        // 处理结果，显示在AI消息中
                        let resultText = '';
                        
                        // 优先查找报告内容
                        if (data.result && data.result.report_content) {
                            resultText = data.result.report_content;
                            console.log("显示报告文件内容");
                        }
                        // 其次查找响应内容
                        else if (data.result && data.result.response) {
                            resultText = data.result.response;
                            console.log("显示响应内容");
                        } 
                        // 再次查找原始结果中的报告内容
                        else if (data.result && data.result.raw_result && data.result.raw_result.report_content) {
                            resultText = data.result.raw_result.report_content;
                            console.log("显示原始结果中的报告内容");
                        }
                        // 再次查找原始结果中的响应
                        else if (data.result && data.result.raw_result && data.result.raw_result.response) {
                            resultText = data.result.raw_result.response;
                            console.log("显示原始结果中的响应");
                        } 
                        // 查找直接作为字符串的结果
                        else if (typeof data.result === 'string') {
                            resultText = data.result;
                            console.log("显示字符串结果");
                        } 
                        // 尝试JSON序列化结果作为后备
                        else {
                            try {
                                resultText = '未找到有效的分析结果。原始数据:\n\n```json\n' + 
                                            JSON.stringify(data.result, null, 2) + 
                                            '\n```';
                                console.log("显示JSON序列化结果");
                            } catch (e) {
                                resultText = '无法显示结果数据';
                                console.error("序列化结果失败:", e);
                            }
                        }
                        
                        console.log("最终输出结果类型:", typeof resultText);
                        console.log("最终输出结果长度:", resultText ? resultText.length : 0);
                        // 只显示输出的前100个字符，避免日志过长
                        if (resultText && resultText.length > 100) {
                            console.log("最终输出结果前100字符:", resultText.substring(0, 100) + "...");
                        } else {
                            console.log("最终输出结果:", resultText);
                        }
                        
                        const logsText = formatLogs(logs);
                        
                        // 检查结果是否为Markdown格式，如果不是则添加格式化
                        if (resultText && !resultText.includes('#') && !resultText.includes('```')) {
                            // 结果看起来不像Markdown，添加基本格式
                            resultText = `## 分析结果\n\n${resultText}`;
                        }
                        
                        // 如果日志很长，但结果较短，直接将结果放在前面
                        let aiContent = '';
                        if (logsText.length > 1000 && resultText.length < 5000) {
                            aiContent = `${resultText}\n\n### 处理过程：\n\`\`\`\n${logsText}\n\`\`\``;
                        } else {
                            aiContent = `### 处理过程：\n\`\`\`\n${logsText}\n\`\`\`\n\n${resultText}`;
                        }
                        
                        addAIMessage(aiContent);
                        
                        // 记录最后使用的promptId，用于多轮对话
                        lastUsedPromptId = promptId;
                        console.log(`成功记录lastUsedPromptId: ${promptId}`);
                        
                        // 将AI回复添加到当前对话
                        currentConversation.messages.push({
                            role: 'ai',
                            content: aiContent,
                            timestamp: new Date().toISOString()
                        });
                        
                        // 确保当前对话的lastUsedPromptId被更新
                        currentConversation.lastUsedPromptId = promptId;
                        
                        saveConversations();
                        updateSidebar();
                        
                        showStatusMessage('分析完成', 'success');
                    } else {
                        // 处理失败
                        const errorMessage = data.result && data.result.message ? data.result.message : '未知错误';
                        const aiContent = `处理失败: ${errorMessage}`;
                        addAIMessage(aiContent);
                        
                        // 将错误消息添加到当前对话
                        currentConversation.messages.push({
                            role: 'ai',
                            content: aiContent,
                            timestamp: new Date().toISOString()
                        });
                        
                        // 确保当前对话的lastUsedPromptId被更新
                        currentConversation.lastUsedPromptId = promptId;
                        
                        saveConversations();
                        updateSidebar();
                        
                        showStatusMessage(`处理失败: ${errorMessage}`, 'error');
                    }
                    
                    isProcessing = false;
                }
            } catch (e) {
                console.error('处理SSE消息出错:', e, "原始数据:", event.data);
            }
        };
        
        // 处理错误
        eventSource.onerror = (error) => {
            console.error('SSE连接错误:', error);
            
            // 尝试重新连接
            let reconnectAttempts = 0;
            const maxReconnectAttempts = 3;
            
            const reconnect = () => {
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    console.log(`尝试重新连接 (${reconnectAttempts}/${maxReconnectAttempts})...`);
                    
                    // 等待一段时间后重试
                    setTimeout(() => {
                        // 使用新的时间戳创建新连接
                        const newTimestamp = new Date().getTime();
                        const newSseUrl = `/expert_api/analyze_stream?prompt_id=${promptId}&t=${newTimestamp}&retry=${reconnectAttempts}`;
                        
                        console.log(`重新创建SSE连接: ${newSseUrl}`);
                        eventSource.close();
                        const newEventSource = new EventSource(newSseUrl);
                        
                        // 将新的事件处理器复制到新连接
                        newEventSource.onmessage = eventSource.onmessage;
                        newEventSource.onerror = eventSource.onerror;
                        
                        // 更新引用
                        eventSource = newEventSource;
                    }, 1000 * reconnectAttempts); // 递增等待时间
                    
                    return;
                }
                
                // 达到最大重试次数后放弃
                eventSource.close();
                
                // 移除处理中消息
                removeProcessingMessage(processingMessageId);
                
                // 显示错误消息
                const errorContent = '连接中断，请重试';
                addAIMessage(errorContent);
                
                // 将错误消息添加到当前对话
                currentConversation.messages.push({
                    role: 'ai',
                    content: errorContent,
                    timestamp: new Date().toISOString()
                });
                
                // 确保当前对话的lastUsedPromptId被更新
                currentConversation.lastUsedPromptId = promptId;
                
                saveConversations();
                updateSidebar();
                
                showStatusMessage('连接中断，请重试', 'error');
                
                isProcessing = false;
            };
            
            reconnect();
        };
        
    } catch (error) {
        console.error('处理提示词出错:', error);
        
        if (processingMessageId) {
            removeProcessingMessage(processingMessageId);
        }
        
        const errorContent = `处理失败: ${error.message}`;
        addAIMessage(errorContent);
        
        // 将错误消息添加到当前对话
        if (currentConversation) {
            currentConversation.messages.push({
                role: 'ai',
                content: errorContent,
                timestamp: new Date().toISOString()
            });
            saveConversations();
            updateSidebar();
        }
        
        showStatusMessage(`处理失败: ${error.message}`, 'error');
        isProcessing = false;
    }
}

// 添加用户消息到聊天区域
function addUserMessage(message, saveToHistory = false) {
    const chatArea = document.querySelector('.flex-1.overflow-y-auto.p-4 .flex.flex-col.gap-6');
    if (!chatArea) return;
    
    const userMessageElement = document.createElement('div');
    userMessageElement.className = 'flex items-start gap-4 justify-end';
    
    // 计算消息长度，自适应宽度
    let messageWidth = 'max-w-[80%]';
    if (message.length < 50) {
        messageWidth = 'max-w-[60%]';
    } else if (message.length > 200) {
        messageWidth = 'max-w-[95%]';
    }
    
    userMessageElement.innerHTML = `
        <div class="flex-1 text-right">
            <div class="bg-[#2A2A2A] p-4 rounded-lg ${messageWidth} ml-auto break-words">
                ${message}
            </div>
        </div>
    `;
    
    chatArea.appendChild(userMessageElement);
    
    // 滚动到底部
    chatArea.scrollTop = chatArea.scrollHeight;
}

// 添加处理中消息
function addProcessingMessage(initialMessage) {
    const chatArea = document.querySelector('.flex-1.overflow-y-auto.p-4 .flex.flex-col.gap-6');
    if (!chatArea) return null;
    
    const messageId = `processing-message-${Date.now()}`;
    const processingElement = document.createElement('div');
    processingElement.className = 'flex items-start gap-4 processing-message';
    processingElement.id = messageId;
    processingElement.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center overflow-hidden">
            <img src="/static/LOGO.jpg" alt="AI" class="w-full h-full object-cover">
        </div>
        <div class="flex-1">
            <div class="bg-[#2A2A2A] p-4 rounded-lg relative markdown-content">
                <div class="mb-2 font-medium">正在处理中...</div>
                <pre class="process-log text-xs text-gray-300 overflow-y-auto max-h-[300px] p-2 bg-[#1a1a1a] rounded" style="white-space: pre-wrap;">${initialMessage}</pre>
            </div>
        </div>
    `;
    
    chatArea.appendChild(processingElement);
    
    // 滚动到底部
    chatArea.scrollTop = chatArea.scrollHeight;
    
    return messageId;
}

// 更新处理中消息
function updateProcessingMessage(messageId, content) {
    const processingElement = document.getElementById(messageId);
    if (!processingElement) return;
    
    const logContainer = processingElement.querySelector('pre.process-log');
    if (logContainer) {
        const wasScrolledToBottom = 
            logContainer.scrollHeight - logContainer.clientHeight <= logContainer.scrollTop + 50;
        
        logContainer.textContent = content;
        
        // 如果之前是滚动到底部的，那么保持滚动到底部
        if (wasScrolledToBottom) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // 滚动聊天区域到底部
        const chatArea = document.querySelector('.flex-1.overflow-y-auto.p-4 .flex.flex-col.gap-6');
        if (chatArea) {
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    }
}

// 移除处理中消息
function removeProcessingMessage(messageId) {
    const processingElement = document.getElementById(messageId);
    if (processingElement) {
        processingElement.remove();
    }
}

// 添加AI思考中状态
function addThinkingMessage() {
    const chatArea = document.querySelector('.flex-1.overflow-y-auto.p-4 .flex.flex-col.gap-6');
    if (!chatArea) return null;
    
    const messageId = `thinking-indicator-${Date.now()}`;
    const thinkingElement = document.createElement('div');
    thinkingElement.className = 'flex items-start gap-4 thinking-message';
    thinkingElement.id = messageId;
    thinkingElement.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center overflow-hidden">
            <img src="/static/LOGO.jpg" alt="AI" class="w-full h-full object-cover">
        </div>
        <div class="flex-1">
            <div class="bg-[#2A2A2A] p-4 rounded-lg relative">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    
    chatArea.appendChild(thinkingElement);
    
    // 滚动到底部
    chatArea.scrollTop = chatArea.scrollHeight;
    
    return messageId;
}

// 移除思考中状态
function removeThinkingMessage(messageId) {
    if (!messageId) {
        // 向后兼容老方式
        const thinkingIndicator = document.getElementById('thinking-indicator');
        if (thinkingIndicator) {
            thinkingIndicator.remove();
        }
        return;
    }
    
    const thinkingElement = document.getElementById(messageId);
    if (thinkingElement) {
        thinkingElement.remove();
    }
}

// 添加AI消息到聊天区域
function addAIMessage(message) {
    const chatArea = document.querySelector('.flex-1.overflow-y-auto.p-4 .flex.flex-col.gap-6');
    if (!chatArea) return;
    
    const aiMessageElement = document.createElement('div');
    aiMessageElement.className = 'flex items-start gap-4';
    
    // 使用marked.js渲染Markdown
    let renderedContent = '';
    try {
        renderedContent = marked.parse(message);
    } catch (e) {
        console.error('Markdown渲染失败:', e);
        renderedContent = `<p>内容渲染失败: ${e.message}</p><pre>${message}</pre>`;
    }
    
    aiMessageElement.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center overflow-hidden">
            <img src="/static/LOGO.jpg" alt="AI" class="w-full h-full object-cover">
        </div>
        <div class="flex-1">
            <div class="bg-[#2A2A2A] p-4 rounded-lg relative markdown-content">
                ${renderedContent}
                <button class="absolute bottom-4 right-4 bg-[#404040] hover:bg-[#505050] px-3 py-1.5 !rounded-button text-sm flex items-center gap-2 copy-button">
                    <i class="fas fa-copy"></i>
                    复制内容
                </button>
            </div>
        </div>
    `;
    
    chatArea.appendChild(aiMessageElement);
    
    // 高亮代码块
    try {
        if (window.hljs) {
            aiMessageElement.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        } else {
            console.warn('highlight.js未加载，代码块不会高亮显示');
        }
    } catch (e) {
        console.error('代码高亮失败:', e);
    }
    
    // 绑定复制按钮事件
    const copyButton = aiMessageElement.querySelector('.copy-button');
    if (copyButton) {
        copyButton.addEventListener('click', () => {
            navigator.clipboard.writeText(message)
                .then(() => {
                    showStatusMessage('已复制到剪贴板', 'success');
                })
                .catch(err => {
                    console.error('复制失败:', err);
                    showStatusMessage('复制失败', 'error');
                });
        });
    }
    
    // 滚动到底部
    chatArea.scrollTop = chatArea.scrollHeight;
}

// 显示状态消息
function showStatusMessage(message, type = 'info') {
    // 先移除可能存在的状态消息
    const existingStatus = document.getElementById('statusMessage');
    if (existingStatus) {
        existingStatus.remove();
    }
    
    // 创建新的状态消息
    const statusElement = document.createElement('div');
    statusElement.id = 'statusMessage';
    statusElement.textContent = message;
    
    // 根据类型设置样式
    switch (type) {
        case 'error':
            statusElement.className = 'status-error';
            break;
        case 'success':
            statusElement.className = 'status-success';
            break;
        case 'processing':
        case 'uploading':
            statusElement.className = 'status-processing';
            break;
        default:
            statusElement.className = 'status-info';
    }
    
    // 添加到页面
    document.body.appendChild(statusElement);
    
    // 自动隐藏（除非是处理中的消息）
    if (type !== 'processing' && type !== 'uploading') {
        setTimeout(() => {
            if (statusElement.parentNode) {
                statusElement.style.opacity = '0';
                setTimeout(() => {
                    if (statusElement.parentNode) {
                        statusElement.remove();
                    }
                }, 300);
            }
        }, 3000);
    }
}

// 切换侧边栏
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    
    if (!sidebar) {
        console.error('未找到侧边栏元素');
        return;
    }
    
    if (sidebar.style.display !== 'none') {
        // 隐藏侧边栏
        sidebar.style.display = 'none';
        
        // 展开主内容区域
        const mainContent = document.querySelector('.flex-1.flex.flex-col');
        if (mainContent) {
            mainContent.style.marginLeft = '0';
            mainContent.style.width = '100%';
        }
    } else {
        // 显示侧边栏
        sidebar.style.display = 'flex';
        
        // 调整主内容区域，防止内容被遮挡
        const mainContent = document.querySelector('.flex-1.flex.flex-col');
        if (mainContent) {
            mainContent.style.marginLeft = '';
            mainContent.style.width = '';
        }
        
        // 加载历史对话
        updateSidebar();
    }
}

// 切换提示词面板
function togglePromptPanel() {
    const promptPanel = document.getElementById('promptPanel');
    const promptPanelTitle = document.getElementById('promptPanelTitle');
    const promptPanelIcon = document.getElementById('promptPanelIcon');
    const searchContainer = document.querySelector('.search-container');
    
    if (promptPanel.classList.contains('w-[320px]')) {
        promptPanel.classList.remove('w-[320px]');
        promptPanel.classList.add('w-[60px]');
        promptPanelTitle.classList.add('opacity-0');
        searchContainer.classList.add('opacity-0');
        promptPanelIcon.classList.remove('fa-chevron-right');
        promptPanelIcon.classList.add('fa-chevron-left');
    } else {
        promptPanel.classList.remove('w-[60px]');
        promptPanel.classList.add('w-[320px]');
        promptPanelTitle.classList.remove('opacity-0');
        searchContainer.classList.remove('opacity-0');
        promptPanelIcon.classList.remove('fa-chevron-left');
        promptPanelIcon.classList.add('fa-chevron-right');
    }
} 