import MarkdownIt from 'markdown-it'

export default defineNuxtPlugin(() => {
    const md = new MarkdownIt({
        html: false,
        linkify: true,
        typographer: true,
        breaks: true
    })

    return {
        provide: {
            md: md
        }
    }
})
