document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const codeBlocks = document.getElementById('codeBlocks');
    const fileList = document.getElementById('fileList');

    analyzeBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            alert('Please enter a URL');
            return;
        }

        // Show loading state
        loading.classList.remove('hidden');
        results.classList.add('hidden');
        codeBlocks.innerHTML = '';
        fileList.innerHTML = '';

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });

            const data = await response.json();
            
            if (response.ok) {
                // Display code blocks
                data.code_blocks.forEach((code, index) => {
                    const pre = document.createElement('pre');
                    pre.className = 'bg-gray-100 p-4 rounded-lg overflow-x-auto';
                    pre.textContent = code;
                    codeBlocks.appendChild(pre);
                });

                // Display file links
                data.file_links.forEach(file => {
                    const div = document.createElement('div');
                    div.className = 'flex items-center justify-between bg-gray-50 p-3 rounded';
                    
                    const span = document.createElement('span');
                    span.textContent = file.filename;
                    
                    const button = document.createElement('button');
                    button.className = 'bg-green-600 text-white px-4 py-1 rounded hover:bg-green-700 transition-colors';
                    button.textContent = 'Download';
                    button.onclick = () => downloadFile(file.url, file.filename);
                    
                    div.appendChild(span);
                    div.appendChild(button);
                    fileList.appendChild(div);
                });

                results.classList.remove('hidden');
            } else {
                alert(data.error || 'An error occurred');
            }
        } catch (error) {
            alert('An error occurred while analyzing the URL');
        } finally {
            loading.classList.add('hidden');
        }
    });

    async function downloadFile(url, filename) {
        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url, filename }),
            });

            const data = await response.json();
            
            if (response.ok) {
                alert(`File downloaded successfully to: ${data.path}`);
            } else {
                alert(data.error || 'Failed to download file');
            }
        } catch (error) {
            alert('An error occurred while downloading the file');
        }
    }
}); 