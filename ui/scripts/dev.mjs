import { spawn } from 'child_process';

const nuxt = spawn('npx', ['nuxt', 'dev'], {
    stdio: ['inherit', 'pipe', 'pipe'],
    shell: true,
    env: { ...process.env }
});

let serverReady = false;
let skipLines = 0;

nuxt.stdout.on('data', (data) => {
    const text = data.toString();
    const lines = text.split('\n');

    for (const line of lines) {
        // Skip QR code block (detect by special unicode characters used in QR codes)
        if (line.includes('▀') || line.includes('█') || line.includes('▄') ||
            line.includes('▌') || line.includes('▐') || line.includes('░')) {
            continue;
        }

        // Skip Network line
        if (line.includes('Network:') || line.includes('[QR code]')) {
            continue;
        }

        // Skip empty lines that are part of QR code spacing
        if (skipLines > 0) {
            skipLines--;
            continue;
        }

        // Replace 0.0.0.0 with localhost in Local: line
        let output = line;
        if (line.includes('Local:') && line.includes('0.0.0.0')) {
            output = line.replace('0.0.0.0', 'localhost');
        }

        // Print the line
        if (output.trim() || line === '') {
            console.log(output);
        }

        // Detect server ready and print our custom message
        if ((line.includes('Nitro server built') || line.includes('Nitro built')) && !serverReady) {
            serverReady = true;
            setTimeout(() => {
                console.log('');
                console.log('╔═══════════════════════════════════════════╗');
                console.log('║  ✨ PyFlow UI is ready!                   ║');
                console.log('║                                           ║');
                console.log('║  Access at: http://localhost:3000/        ║');
                console.log('╚═══════════════════════════════════════════╝');
                console.log('');
            }, 500);
        }
    }
});

nuxt.stderr.on('data', (data) => {
    process.stderr.write(data);
});

nuxt.on('close', (code) => {
    process.exit(code || 0);
});
