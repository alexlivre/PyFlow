import { defineStore } from 'pinia'

export const usePyFlowStore = defineStore('pyflow', {
    state: () => ({
        // Code Execution
        code: '# Escreva seu código Python aqui\nprint("Olá, PyFlow local!")\n',
        output: null,
        isRunning: false,
        consoleStream: '',
        streamBuffer: '',

        // Chat
        chatHistory: [],
        isChatting: false,

        // Socratic Hint
        hintText: '',
        hintLevel: 0,
        hintTarget: null,
        isHinting: false,

        // Configuration
        activeConfigId: 'default',
        apiToken: '',
        apiOnline: null,
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

        async refreshHealth() {
            try {
                await $fetch('/api/health', { headers: { 'X-PyFlow-Token': this.apiToken } })
                this.apiOnline = true
            } catch (e) {
                this.apiOnline = false
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
                this.syncHintTarget()

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
                this.syncHintTarget()
            } finally {
                this.isRunning = false
            }
        },

        async runCodeStreaming() {
            this.saveCodeToStorage()
            this.isRunning = true
            this.output = null
            this.consoleStream = ''
            this.streamBuffer = ''
            this.activeTab = 'console'

            const config = this.configs.find(c => c.id === this.activeConfigId)
            const headers = this.apiToken ? { 'X-PyFlow-Token': this.apiToken } : {}

            try {
                const res = await fetch('/api/run/stream', {
                    method: 'POST',
                    headers: { ...headers, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: this.code,
                        ai_config: config ? {
                            provider: config.provider,
                            model_id: config.model_id,
                            api_key: config.api_key || undefined,
                            base_url: config.base_url || undefined
                        } : undefined,
                        ai_explain_on_error: true,
                        include_raw_traceback: true
                    })
                })
                if (!res.ok) throw new Error('HTTP ' + res.status)
                const reader = res.body.getReader()
                const decoder = new TextDecoder()
                let receivedTerminal = false
                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break
                    this.streamBuffer += decoder.decode(value, { stream: true })
                    const lines = this.streamBuffer.split('\n')
                    this.streamBuffer = lines.pop() || ''
                    for (const line of lines) {
                        if (!line.trim()) continue
                        let evt
                        try {
                            evt = JSON.parse(line)
                        } catch (e) {
                            continue
                        }
                        if (evt.type === 'output') {
                            this.consoleStream += evt.data
                        } else if (evt.type === 'done') {
                            receivedTerminal = true
                            this.output = evt.result
                            this.syncHintTarget()
                            if (evt.result.diagnostics || evt.result.ai_error_help) this.activeTab = 'diagnostics'
                        } else if (evt.type === 'error') {
                            receivedTerminal = true
                            this.output = {
                                status: 'error',
                                stderr: evt.message,
                                stdout: '',
                                execution_time_ms: 0
                            }
                            this.syncHintTarget()
                        }
                    }
                }
                if (!receivedTerminal && this.output === null) {
                    this.output = {
                        status: 'error',
                        stdout: this.consoleStream,
                        stderr: 'Stream encerrado sem resposta final (servidor caiu?).',
                        execution_time_ms: 0
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

        syncHintTarget() {
            const id = this.output?.request_id || null
            if (id !== this.hintTarget) {
                this.hintTarget = id
                this.hintLevel = 0
                this.hintText = ''
            }
        },

        async requestHint(level) {
            this.isHinting = true
            const config = this.configs.find(c => c.id === this.activeConfigId)
            const headers = this.apiToken ? { 'X-PyFlow-Token': this.apiToken } : {}

            try {
                const res = await $fetch('/api/hint', {
                    method: 'POST',
                    headers,
                    body: {
                        code: this.code,
                        level,
                        diagnostics: this.output?.diagnostics || undefined,
                        ai_config: config ? {
                            provider: config.provider,
                            model_id: config.model_id,
                            api_key: config.api_key || undefined,
                            base_url: config.base_url || undefined
                        } : undefined
                    }
                })

                this.hintText = res.hint
                this.hintLevel = level
            } catch (err) {
                this.hintText = 'Erro ao solicitar dica: ' + err.message
            } finally {
                this.isHinting = false
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
