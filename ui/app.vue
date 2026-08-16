<template>
  <div class="h-screen flex flex-col overflow-hidden">
    <!-- Header -->
    <header class="app-header">
      <div class="app-logo">
        <div class="flex items-center gap-3">
          <!-- Logo Icon -->
          <div class="relative">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="32" height="32" rx="8" fill="url(#logoGradient)"/>
              <path d="M10 22V10h4.5c1.2 0 2.1.3 2.8.9.7.6 1 1.4 1 2.4 0 1-.3 1.8-1 2.4-.7.6-1.6.9-2.8.9H12.5v5.4H10z" fill="white"/>
              <path d="M20 15l3 3.5-3 3.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <defs>
                <linearGradient id="logoGradient" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#6366f1"/>
                  <stop offset="1" stop-color="#a855f7"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div>
            <h1 class="app-logo-text text-gradient">PyFlow</h1>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4">
          <span class="badge badge-primary">
            <span class="status-dot status-dot-success mr-2"></span>
            Connected
          </span>
        </div>
      </div>
      
      <div class="flex items-center gap-3">
        <!-- Model Selector -->
        <div class="relative">
          <select v-model="store.activeConfigId" class="select" style="width: 200px;">
            <option v-for="c in store.configs" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        
        <!-- Settings Button -->
        <button class="btn btn-icon btn-ghost" title="Settings" @click="store.showSettings = true">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.1a2 2 0 0 1-1-1.72v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>

        <!-- Keyboard Shortcut Hint -->
        <div class="hidden lg:flex items-center gap-2 text-xs text-muted px-3">
          <kbd class="kbd">Ctrl</kbd>
          <span>+</span>
          <kbd class="kbd">Enter</kbd>
          <span class="ml-1">to run</span>
        </div>
        
        <!-- Run Button -->
        <button 
          class="btn btn-primary run-button" 
          :disabled="store.isRunning" 
          @click="store.runCode"
          style="min-width: 120px;"
        >
          <template v-if="!store.isRunning">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            <span>Run Code</span>
          </template>
          <template v-else>
            <div class="spinner"></div>
            <span>Running...</span>
          </template>
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 flex overflow-hidden">
      <!-- Left: Editor Panel -->
      <div class="flex-1 flex flex-col editor-panel">
        <!-- Editor Header -->
        <div class="flex items-center justify-between px-4 py-2 border-b border-border bg-elevated">
          <div class="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-accent">
              <polyline points="16 18 22 12 16 6"/>
              <polyline points="8 6 2 12 8 18"/>
            </svg>
            <span class="text-sm font-medium text-secondary">main.py</span>
          </div>
          <div class="flex items-center gap-2">
            <button class="btn btn-ghost text-xs" @click="clearCode" title="Clear code">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
              </svg>
              Clear
            </button>
            <button class="btn btn-ghost text-xs" @click="loadExample" title="Load example">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
              </svg>
              Example
            </button>
          </div>
        </div>
        
        <!-- Code Editor -->
        <div class="flex-1 relative">
          <ClientOnly>
            <Codemirror
              v-model="store.code"
              placeholder="# Write your Python code here..."
              :style="{ height: '100%' }"
              :autofocus="true"
              :indent-with-tab="true"
              :tab-size="4"
              :extensions="extensions"
              @ready="onEditorReady"
              @keydown="handleEditorKeydown"
            />
          </ClientOnly>
        </div>
      </div>

      <!-- Right: Results Panel -->
      <div class="results-panel flex flex-col" style="width: 45%; min-width: 400px;">
        <!-- Tab Navigation -->
        <div class="tab-nav">
          <button 
            class="tab-btn"
            :class="{ active: store.activeTab === 'console' }"
            @click="store.activeTab = 'console'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2">
              <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
            </svg>
            Console
          </button>
          <button 
            class="tab-btn"
            :class="{ active: store.activeTab === 'diagnostics' }"
            @click="store.activeTab = 'diagnostics'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            Diagnostics
            <span v-if="hasDiagnostics" class="ml-2 status-dot status-dot-error"></span>
          </button>
          <button 
            class="tab-btn"
            :class="{ active: store.activeTab === 'chat' }"
            @click="store.activeTab = 'chat'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            AI Chat
          </button>
        </div>

        <!-- Tab Content -->
        <div class="flex-1 overflow-hidden relative">
          <!-- Console Output -->
          <div v-if="store.activeTab === 'console'" class="h-full flex flex-col">
            <div v-if="store.output" class="flex-1 overflow-auto p-5">
              <div class="console-output">
                <pre v-if="store.output.stdout" class="console-stdout whitespace-pre-wrap break-words m-0 mb-4">{{ store.output.stdout }}</pre>
                <pre v-if="store.output.stderr" class="console-stderr whitespace-pre-wrap break-words m-0">{{ store.output.stderr }}</pre>
              </div>
              
              <!-- Execution Stats -->
              <div class="mt-6 pt-4 border-t border-border flex items-center justify-between text-xs">
                <div class="flex items-center gap-4">
                  <div class="flex items-center gap-2">
                    <span class="text-muted">Status:</span>
                    <span :class="store.output.status === 'success' ? 'badge badge-success' : 'badge badge-error'">
                      {{ store.output.status }}
                    </span>
                  </div>
                </div>
                <div class="flex items-center gap-2 text-muted">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                  </svg>
                  {{ store.output.execution_time_ms }}ms
                </div>
              </div>
            </div>
            
            <!-- Empty State -->
            <div v-else class="empty-state">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="empty-state-icon">
                <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
              </svg>
              <h3 class="empty-state-title">No Output Yet</h3>
              <p class="empty-state-description">
                Write some Python code and click <strong>Run Code</strong> or press <kbd class="kbd">Ctrl+Enter</kbd> to execute.
              </p>
            </div>
          </div>

          <!-- Diagnostics -->
          <div v-else-if="store.activeTab === 'diagnostics'" class="h-full overflow-auto p-5">
            <div v-if="store.output && (store.output.diagnostics || store.output.ai_error_help)" class="space-y-4">
              <!-- Error Card -->
              <div v-if="store.output.diagnostics" class="diagnostic-card animate-fade-in">
                <div class="diagnostic-card-header">
                  <span class="badge badge-error">Error</span>
                  <h3 class="font-semibold text-error">{{ store.output.diagnostics.error_type }}</h3>
                </div>
                <p class="text-secondary mb-3">{{ store.output.diagnostics.message }}</p>
                <div v-if="store.output.diagnostics.line" class="text-xs text-muted flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="m9 12 2 2 4-4"/>
                  </svg>
                  Line {{ store.output.diagnostics.line }}
                </div>
              </div>
              
              <!-- AI Suggestion Card -->
              <div v-if="store.output.ai_error_help" class="ai-suggestion-card animate-slide-up">
                <div class="flex items-center gap-3 mb-4">
                  <span class="badge badge-primary badge-glow">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-1">
                      <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/><path d="M8.5 8.5v.01"/><path d="M16 15.5v.01"/><path d="M12 12v.01"/><path d="M11 17v.01"/><path d="M7 14v.01"/>
                    </svg>
                    AI Analysis
                  </span>
                </div>
                
                <h4 class="font-semibold mb-2">Suggested Fix</h4>
                <p class="text-secondary text-sm mb-4">{{ store.output.ai_error_help.probable_fix }}</p>
                
                <div v-if="store.output.ai_error_help.suggested_code">
                  <h5 class="text-xs uppercase tracking-wide text-muted mb-2 font-semibold">Corrected Code</h5>
                  <div class="code-block accent-border-l">
                    <pre class="code-font text-sm"><code>{{ store.output.ai_error_help.suggested_code }}</code></pre>
                  </div>
                  
                  <button class="btn btn-success w-full mt-4" @click="applyFix(store.output.ai_error_help.suggested_code)">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="m9 12 2 2 4-4"/>
                    </svg>
                    Apply Fix
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Empty State -->
            <div v-else class="empty-state">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="empty-state-icon">
                <circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>
              </svg>
              <h3 class="empty-state-title">All Clear!</h3>
              <p class="empty-state-description">
                No errors or diagnostics to display. Your code is running smoothly.
              </p>
            </div>
          </div>

          <!-- AI Chat -->
          <div v-else-if="store.activeTab === 'chat'" class="flex flex-col h-full">
            <!-- Chat Messages -->
            <div class="flex-1 overflow-y-auto p-5 space-y-4" ref="chatContainer">
              <div v-if="store.chatHistory.length === 0" class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="empty-state-icon">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <h3 class="empty-state-title">Start a Conversation</h3>
                <p class="empty-state-description">
                  Ask the AI about your code, get explanations, or request help with Python concepts.
                </p>
              </div>
              
              <div v-else v-for="(msg, i) in store.chatHistory" :key="i" 
                  class="flex animate-fade-in"
                  :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
                <div class="max-w-[85%]">
                  <div 
                    class="chat-bubble"
                    :class="msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'"
                  >
                    <!-- User message: plain text -->
                    <template v-if="msg.role === 'user'">{{ msg.content }}</template>
                    <!-- Assistant message: render as Markdown -->
                    <div v-else class="markdown-content" v-html="renderMarkdown(msg.content)"></div>
                  </div>
                  <div class="text-xs text-muted mt-1" :class="msg.role === 'user' ? 'text-right' : 'text-left'">
                    {{ msg.role === 'user' ? 'You' : 'AI Assistant' }}
                  </div>
                </div>
              </div>
              
              <!-- Typing Indicator -->
              <div v-if="store.isChatting" class="flex justify-start animate-fade-in">
                <div class="chat-bubble chat-bubble-assistant">
                  <div class="flex items-center gap-1">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Chat Input -->
            <div class="p-4 border-t border-border bg-elevated">
              <form @submit.prevent="sendMessage" class="flex gap-3">
                <input 
                  v-model="chatInput" 
                  class="input flex-1" 
                  placeholder="Ask AI about your code..." 
                  :disabled="store.isChatting"
                />
                <button 
                  type="submit" 
                  class="btn btn-primary" 
                  :disabled="!chatInput.trim() || store.isChatting"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                  </svg>
                  Send
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </main>
    
    <!-- Settings Modal -->
    <Teleport to="body">
      <div v-if="store.showSettings" class="modal-overlay" @click.self="store.showSettings = false">
        <div class="modal-content" style="width: 600px;">
          <!-- Modal Header -->
          <div class="flex items-center justify-between p-5 border-b border-border">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-primary-soft">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-accent">
                  <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.1a2 2 0 0 1-1-1.72v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </div>
              <div>
                <h2 class="text-lg font-semibold">Settings</h2>
                <p class="text-xs text-muted">Manage your AI model configurations</p>
              </div>
            </div>
            <button @click="store.showSettings = false" class="btn btn-ghost btn-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          
          <!-- Modal Body -->
          <div class="p-5 overflow-y-auto" style="max-height: 60vh;">
            <!-- Config List -->
            <div class="space-y-3">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-sm font-semibold text-muted uppercase tracking-wide">Model Profiles</h3>
                <button class="btn text-xs" @click="createNewConfig">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  Add New
                </button>
              </div>
              
              <div v-for="c in store.configs" :key="c.id" class="config-card">
                <div class="flex items-center gap-3">
                  <div class="p-2 rounded-lg bg-surface">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-secondary">
                      <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
                    </svg>
                  </div>
                  <div>
                    <div class="font-medium">{{ c.name }}</div>
                    <div class="text-xs text-muted">{{ c.provider }} / {{ c.model_id }}</div>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span v-if="c.id === store.activeConfigId" class="badge badge-success text-xs">Active</span>
                  <button class="btn btn-ghost text-xs" @click="editConfig(c)">Edit</button>
                  <button 
                    v-if="store.configs.length > 1" 
                    class="btn btn-ghost text-xs text-error" 
                    @click="store.deleteConfig(c.id)"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
            
            <div v-if="editingConfig" class="mt-6 pt-6 border-t border-border animate-slide-up">
              <h3 class="font-semibold mb-4">{{ isNewConfig ? 'New Configuration' : 'Edit Configuration' }}</h3>
              
              <div class="space-y-4">
                <div class="form-group">
                  <label class="form-label">Profile Name</label>
                  <input v-model="editingConfig.name" class="input" placeholder="e.g., GPT-5 Turbo" />
                </div>
                
                <div class="grid grid-cols-2 gap-4">
                  <div class="form-group">
                    <label class="form-label">Provider</label>
                    <select v-model="editingConfig.provider" class="select">
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="google">Google Gemini</option>
                      <option value="deepseek">DeepSeek</option>
                      <option value="openrouter">OpenRouter</option>
                      <option value="ollama">Ollama (Local)</option>
                    </select>
                    <p v-if="editingConfig.provider === 'openrouter'" class="text-xs text-muted mt-1">
                      OpenRouter: Use model IDs like "openai/gpt-4o" or "anthropic/claude-3.5-sonnet"
                    </p>
                  </div>
                    <div class="form-group">
                    <label class="form-label">Model ID</label>
                    
                    <!-- Search and Filter Controls for OpenRouter -->
                    <div v-if="editingConfig.provider === 'openrouter' && availableModels.length > 0" class="mb-3 space-y-2 p-3 bg-surface rounded border border-border">
                        <input v-model="modelSearch" class="input w-full text-sm" placeholder="Search models (e.g. mini, claude)..." />
                        <div class="flex flex-wrap gap-2 text-xs items-center">
                          <label class="flex items-center gap-1 cursor-pointer hover:text-white transition-colors">
                            <input type="radio" v-model="modelFilter" value="all" class="accent-primary"> All
                          </label>
                          <label class="flex items-center gap-1 cursor-pointer hover:text-white transition-colors">
                            <input type="radio" v-model="modelFilter" value="free" class="accent-primary"> Free
                          </label>
                          <label class="flex items-center gap-1 cursor-pointer hover:text-white transition-colors">
                            <input type="radio" v-model="modelFilter" value="paid" class="accent-primary"> Paid
                          </label>
                          <span class="ml-auto text-muted">{{ filteredAvailableModels.length }} models</span>
                        </div>
                    </div>

                    <div class="flex gap-2">
                        <div class="flex-1 relative">
                        <!-- Select for OpenRouter models -->
                        <select 
                            v-if="editingConfig.provider === 'openrouter' && availableModels.length > 0" 
                            v-model="editingConfig.model_id" 
                            class="select w-full"
                        >
                            <option value="" disabled>Select a model</option>
                            <option v-for="m in filteredAvailableModels" :key="m.id" :value="m.id">
                            {{ m.name }} {{ isFreeModel(m) ? '(Free)' : '' }}
                            </option>
                        </select>
                        
                        <!-- Standard input for others or fallback -->
                        <input 
                            v-else
                            v-model="editingConfig.model_id" 
                            class="input w-full" 
                            :placeholder="editingConfig.provider === 'openrouter' ? 'e.g., openai/gpt-4o' : 'e.g., gpt-5-nano'" 
                        />
                        </div>
                        
                        <!-- Fetch button for OpenRouter -->
                        <button 
                        v-if="editingConfig.provider === 'openrouter'"
                        class="btn btn-secondary px-3"
                        :disabled="!editingConfig.api_key || isLoadingModels"
                        @click="fetchOpenRouterModels"
                        title="Fetch available models from OpenRouter"
                        >
                        <span v-if="isLoadingModels" class="spinner w-4 h-4"></span>
                        <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
                            <path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
                            <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
                        </svg>
                        </button>
                    </div>
                  </div>
                </div>
                
                <div class="form-group">
                  <label class="form-label">Base URL (Optional)</label>
                  <input v-model="editingConfig.base_url" class="input" placeholder="e.g., http://localhost:11434/v1" />
                </div>
                
                <div class="form-group">
                  <label class="form-label">API Key</label>
                  <input v-model="editingConfig.api_key" type="password" class="input" placeholder="sk-..." />
                </div>
                
                <div class="flex justify-end gap-3 pt-2">
                  <button class="btn" @click="editingConfig = null">Cancel</button>
                  <button class="btn btn-primary" @click="saveEdit">Save Configuration</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { usePyFlowStore } from '~/stores/pyflow'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import { Decoration } from '@codemirror/view'
import { StateEffect, StateField } from '@codemirror/state'

const store = usePyFlowStore()
const chatInput = ref('')
const editingConfig = ref(null)
const isNewConfig = ref(false)
const chatContainer = ref(null)
const availableModels = ref([])
const isLoadingModels = ref(false)
const modelSearch = ref('')
const modelFilter = ref('all') // all, free, paid
const { $md } = useNuxtApp() // Access markdown plugin

const isFreeModel = (model) => {
  if (!model.pricing) return false
  const prompt = parseFloat(model.pricing.prompt || '0')
  const completion = parseFloat(model.pricing.completion || '0')
  return prompt === 0 && completion === 0
}

const filteredAvailableModels = computed(() => {
  if (!availableModels.value.length) return []
  
  let result = availableModels.value
  
  // Apply Search
  if (modelSearch.value) {
    const q = modelSearch.value.toLowerCase()
    result = result.filter(m => 
      m.name.toLowerCase().includes(q) || 
      m.id.toLowerCase().includes(q)
    )
  }
  
  // Apply Filter
  if (modelFilter.value === 'free') {
    result = result.filter(m => isFreeModel(m))
  } else if (modelFilter.value === 'paid') {
    result = result.filter(m => !isFreeModel(m))
  }
  
  return result
})

const editorView = ref(null)
const errorLine = computed(() => store.output?.diagnostics?.line ?? null)

const onEditorReady = (view) => {
  editorView.value = view
}

const setErrorLine = StateEffect.define()
const errorLineField = StateField.define({
  create: () => Decoration.none,
  update(deco, tr) {
    deco = deco.map(tr.changes)
    for (const e of tr.effects) {
      if (e.is(setErrorLine)) {
        deco = Decoration.none
        if (e.value != null) {
          const mark = Decoration.line({
            attributes: { style: 'background: rgba(239,68,68,0.12); border-left: 3px solid #ef4444;' },
          })
          const lineNo = Math.min(e.value, tr.startState.doc.lines)
          deco = deco.add(tr.startState.doc, tr.startState.doc.line(lineNo), mark)
        }
      }
    }
    return deco
  },
})

watch(errorLine, (line) => {
  const view = editorView.value
  if (view) view.dispatch({ effects: setErrorLine.of(line) })
})

const extensions = [python(), oneDark, errorLineField]

// Function to render markdown
const renderMarkdown = (text) => {
  if (!text) return ''
  if ($md) {
    return $md.render(text)
  }
  // Fallback: basic text with line breaks
  return text.replace(/\n/g, '<br>')
}

const fetchOpenRouterModels = async () => {
  if (!editingConfig.value?.api_key) return
  
  isLoadingModels.value = true
  try {
    const response = await $fetch('/api/models/openrouter', {
      headers: {
        'X-OpenRouter-API-Key': editingConfig.value.api_key,
        ...(store.apiToken ? { 'X-PyFlow-Token': store.apiToken } : {})
      }
    })
    
    availableModels.value = response.data
  } catch (error) {
    console.error('Error fetching models:', error)
    // You might want to show a toast notification here
    alert('Failed to fetch OpenRouter models. Please check your API Key.')
  } finally {
    isLoadingModels.value = false
  }
}

onMounted(() => {
  store.loadFromStorage()
  store.fetchToken()

  // Add keyboard shortcut for running code
  window.addEventListener('keydown', handleGlobalKeydown)
})

const hasDiagnostics = computed(() => {
  return store.output && (store.output.diagnostics || store.output.ai_error_help)
})

// Watch chat history and scroll to bottom
watch(() => store.chatHistory.length, async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
})

const handleGlobalKeydown = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    if (!store.isRunning) {
      store.runCode()
    }
  }
}

const handleEditorKeydown = (e) => {
  // Handled by global listener
}

const sendMessage = () => {
  if (!chatInput.value.trim()) return
  store.sendChatMessage(chatInput.value)
  chatInput.value = ''
}

const applyFix = (code) => {
  if (!code) return
  store.code = code
  store.activeTab = 'console'
}

const editConfig = (config) => {
  editingConfig.value = { ...config }
  isNewConfig.value = false
}

const createNewConfig = () => {
  editingConfig.value = {
    id: '', 
    name: 'New Config', 
    provider: 'openai', 
    model_id: '',
    base_url: '',
    api_key: ''
  }
  isNewConfig.value = true
}

const saveEdit = () => {
  if (editingConfig.value) {
    store.saveConfig(editingConfig.value)
    editingConfig.value = null
  }
}

const clearCode = () => {
  store.code = '# Write your Python code here...\n'
}

const loadExample = () => {
  store.code = `# PyFlow Example - Hello World
def greet(name):
    """Returns a greeting message."""
    return f"Hello, {name}! Welcome to PyFlow."

# Main execution
if __name__ == "__main__":
    names = ["Alice", "Bob", "Charlie"]
    
    for name in names:
        message = greet(name)
        print(message)
    
    print("\\n✨ Code executed successfully!")
`
}
</script>

<style>
/* Markdown Styles for Chat */
.markdown-content,
.markdown-body {
  font-size: 0.9em;
  line-height: 1.7;
}

.markdown-content p,
.markdown-body p {
  margin-bottom: 0.8em;
}

.markdown-content p:last-child,
.markdown-body p:last-child {
  margin-bottom: 0;
}

.markdown-content h1, .markdown-content h2, .markdown-content h3,
.markdown-body h1, .markdown-body h2, .markdown-body h3 {
  font-weight: 600;
  margin-top: 1em;
  margin-bottom: 0.5em;
  color: inherit;
}

.markdown-content h3,
.markdown-body h3 {
  font-size: 1.1em;
}

.markdown-content ul, .markdown-content ol,
.markdown-body ul, .markdown-body ol {
  padding-left: 1.5em;
  margin-bottom: 0.8em;
}

.markdown-content li,
.markdown-body li {
  margin-bottom: 0.4em;
}

.markdown-content code,
.markdown-body code {
  font-family: var(--font-mono);
  font-size: 0.85em;
  background: rgba(0, 0, 0, 0.3);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  color: #f0abfc;
}

.markdown-content pre,
.markdown-body pre {
  background: #0a0a12;
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.8em 0;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.markdown-content pre code,
.markdown-body pre code {
  background: transparent;
  padding: 0;
  color: #e5e7eb;
}

.markdown-content strong,
.markdown-body strong {
  font-weight: 600;
  color: #fff;
}

.chat-bubble-user .markdown-content code,
.chat-bubble-user .markdown-body code {
  background: rgba(255, 255, 255, 0.2);
}

/* Keyboard Badge */
.kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.15rem 0.4rem;
  font-size: 0.7rem;
  font-family: var(--font-mono);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  color: var(--text-secondary);
}

/* Typing Indicator */
.typing-dot {
  width: 6px;
  height: 6px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: typingBounce 1.4s infinite both;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typingBounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

/* Primary soft background */
.bg-primary-soft {
  background: rgba(99, 102, 241, 0.1);
}

/* Elevated background */
.bg-elevated {
  background: var(--bg-elevated);
}

/* Hide utilities */
.hidden {
  display: none;
}

@media (min-width: 1024px) {
  .lg\:flex {
    display: flex;
  }
}

/* CodeMirror overrides */
.cm-editor {
  height: 100% !important;
  font-family: var(--font-mono) !important;
  font-size: 14px !important;
  background: #0a0a0f !important;
}

.cm-scroller {
  overflow: auto !important;
}

.cm-gutters {
  background: #0a0a0f !important;
  border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.cm-activeLineGutter {
  background: rgba(99, 102, 241, 0.1) !important;
}

.cm-activeLine {
  background: rgba(99, 102, 241, 0.05) !important;
}
</style>
