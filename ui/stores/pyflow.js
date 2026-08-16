import { defineStore } from 'pinia'

export const usePyFlowStore = defineStore('pyflow', {
    state: () => ({
        // Code Execution
        code: '# Escreva seu código Python aqui\nprint("Olá, PyFlow local!")\n',
        output: null,
        isRunning: false,

        // Chat
        chatHistory: [],
        isChatting: false,

        // Configuration
        activeConfigId: 'default',
        apiToken: '',
        configs: [
            {
                id: 'default',
                name: 'OpenAI GPT-4o',
                provider: 'openai',
                model_id: 'gpt-4o',
                base_url: '',
                api_key: ''
            }
        ],

        // UI State
        showSettings: false,
        activeTab: 'console' // console, diagnostics, chat
    }),

    actions: {
        async fetchToken() {
            if (process.client) {
                try {
                    const res = await $fetch('/api/token')
                    this.apiToken = res.token || ''
                } catch (e) {
                    console.error('Failed to fetch API token:', e)
                }
            }
        },

        async runCode() {
            this.saveCodeToStorage()
            this.isRunning = true
            this.output = null
            this.activeTab = 'console'

            const config = this.configs.find(c => c.id === this.activeConfigId)
            const headers = this.apiToken ? { 'X-PyFlow-Token': this.apiToken } : {}

            try {
                const res = await $fetch('/api/run', {
                    method: 'POST',
                    headers,
                    body: {
                        code: this.code,
                        ai_config: config ? {
                            provider: config.provider,
                            model_id: config.model_id,
                            api_key: config.api_key || undefined,
                            base_url: config.base_url || undefined
                        } : undefined,
                        ai_explain_on_error: true,
                        include_raw_traceback: true
                    }
                })
                this.output = res

                // Auto-switch to diagnostics if error and diagnostics exist
                if (res.status === 'error' || res.diagnostics) {
                    // Only switch if there is something interesting to show besides raw stderr
                    if (res.diagnostics || res.ai_error_help) {
                        this.activeTab = 'diagnostics'
                    }
                }
            } catch (err) {
                this.output = {
                    status: 'error',
                    stderr: 'Falha na comunicação com o servidor.\n' + err.message,
                    stdout: '',
                    execution_time_ms: 0
                }
            } finally {
                this.isRunning = false
            }
        },

        async sendChatMessage(message) {
            this.isChatting = true
            // Add user message optimistically
            // But wait, the API returns the FULL history including the new one.
            // So I can append nicely.
            const currentHistory = [...this.chatHistory]
            this.chatHistory.push({ role: 'user', content: message })

            const config = this.configs.find(c => c.id === this.activeConfigId)
            const headers = this.apiToken ? { 'X-PyFlow-Token': this.apiToken } : {}

            try {
                const res = await $fetch('/api/chat', {
                    method: 'POST',
                    headers,
                    body: {
                        code: this.code,
                        user_message: message,
                        history: currentHistory,
                        ai_config: config ? {
                            provider: config.provider,
                            model_id: config.model_id,
                            api_key: config.api_key || undefined,
                            base_url: config.base_url || undefined
                        } : undefined
                    }
                })

                this.chatHistory = res.history
            } catch (err) {
                this.chatHistory.push({ role: 'assistant', content: 'Erro ao conectar ao chat: ' + err.message })
            } finally {
                this.isChatting = false
            }
        },

        saveConfig(config) {
            const idx = this.configs.findIndex(c => c.id === config.id)
            if (idx >= 0) {
                this.configs[idx] = config
            } else {
                this.configs.push({ ...config, id: Date.now().toString() })
            }
            this.saveToStorage()
        },

        deleteConfig(id) {
            this.configs = this.configs.filter(c => c.id !== id)
            if (this.activeConfigId === id && this.configs.length > 0) {
                this.activeConfigId = this.configs[0].id
            }
            this.saveToStorage()
        },

        saveCodeToStorage: (() => {
            let timer = null
            return function () {
                clearTimeout(timer)
                timer = setTimeout(() => {
                    if (process.client) localStorage.setItem('pyflow_code', this.code)
                }, 500)
            }
        })(),

        saveToStorage() {
            if (process.client) {
                localStorage.setItem('pyflow_configs', JSON.stringify(this.configs))
                localStorage.setItem('pyflow_active_config', this.activeConfigId)
            }
        },

        loadFromStorage() {
            if (process.client) {
                const saved = localStorage.getItem('pyflow_configs')
                if (saved) {
                    try {
                        this.configs = JSON.parse(saved)
                    } catch (e) { }
                }
                const active = localStorage.getItem('pyflow_active_config')
                if (active && this.configs.find(c => c.id === active)) {
                    this.activeConfigId = active
                }
                const savedCode = localStorage.getItem('pyflow_code')
                if (savedCode !== null && savedCode !== '') {
                    this.code = savedCode
                }
            }
        }
    }
})
