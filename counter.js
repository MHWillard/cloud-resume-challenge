const FUNCTION_BASE_URL = window.FUNCTION_BASE_URL || "http://localhost:7071/api";
const counterElement = document.getElementById("visitor-count");

async function updateVisitorCount() {
	try {
		const response = await fetch(`${FUNCTION_BASE_URL}/visitorcount`);
		if (!response.ok) throw new Error(`HTTP ${response.status}`);
		const data = await response.json();
		if (counterElement) {
			counterElement.textContent = `Visitors: ${data.count}`;
		}
	} catch (err) {
		console.error("Failed to update visitor count:", err);
		if (counterElement) {
			counterElement.textContent = "Visitors: --";
		}
	}
}

updateVisitorCount();