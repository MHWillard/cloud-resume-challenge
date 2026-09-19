const counterElement = document.getElementById("visitor-count");

async function updateVisitorCount() {
	try {
		const response = await fetch(`https://mattwillardcloudresume.com/api/visitorcount`);
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