// static/js/script.js

document.getElementById('upload-form').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission

    const formData = new FormData(this);
    const statusDiv = document.getElementById('status');
    const downloadDiv = document.getElementById('download-link');

    statusDiv.innerHTML = "Processing...";
    downloadDiv.innerHTML = "";

    fetch('/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.task_id) {
            // Poll for task status
            const taskId = data.task_id;
            const interval = setInterval(() => {
                fetch(`/task_status/${taskId}`)
                .then(res => res.json())
                .then(statusData => {
                    if (statusData.state === 'SUCCESS') {
                        clearInterval(interval);
                        statusDiv.innerHTML = "Processing completed!";
                        
                        // Extract the filename from the result
                        const outputPath = statusData.result.output_path;
                        const filename = outputPath.split('/').pop();

                        console.log(`Output Path: ${outputPath}`);
                        console.log(`Filename Extracted: ${filename}`);

                        // Create a download link
                        const downloadLink = document.createElement('a');
                        downloadLink.href = `/download/${filename}`;
                        downloadLink.textContent = "Download OCR Result";
                        downloadLink.classList.add('btn', 'btn-success');

                        downloadDiv.appendChild(downloadLink);
                    } else if (statusData.state === 'FAILURE') {
                        clearInterval(interval);
                        statusDiv.innerHTML = "Processing failed.";
                    } else {
                        statusDiv.innerHTML = `Processing: ${statusData.state}`;
                    }
                })
                .catch(error => {
                    clearInterval(interval);
                    statusDiv.innerHTML = "An error occurred while checking task status.";
                    console.error('Error fetching task status:', error);
                });
            }, 3000); // Poll every 3 seconds
        } else if (data.error) {
            statusDiv.innerHTML = `Error: ${data.error}`;
        }
    })
    .catch(error => {
        statusDiv.innerHTML = "An error occurred during the upload.";
        console.error('Error uploading file:', error);
    });
});