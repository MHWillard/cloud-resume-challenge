const counterKey = "visitorCount";
const counterElement = document.getElementById("visitor-count");

if (counterElement) {
	const currentCount = Number(localStorage.getItem(counterKey) || "0") + 1;
	localStorage.setItem(counterKey, String(currentCount));
	counterElement.textContent = `Visitors: ${currentCount}`;
}