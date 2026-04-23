function startPolling({ url, interval = 3000, render }) {
    let intervalId = null;

    async function loadData() {
        try {
            const response = await fetch(url);

            if (!response.ok) {
                console.error("API error:", response.status);
                return;
            }

            const data = await response.json();
            render(data);

        } catch (error) {
            console.error("Polling error:", error);
        }
    }

    function start() {
        loadData();
        intervalId = setInterval(loadData, interval);
    }

    function stop() {
        if (intervalId) {
            clearInterval(intervalId);
        }
    }

    return { start, stop };
}