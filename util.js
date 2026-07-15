// Tab switching logic
const buttons = document.querySelectorAll(".tab-button");
const tabs = document.querySelectorAll(".tab");

buttons.forEach(button => {
    button.onclick = () => {
        tabs.forEach(tab => tab.hidden = true);
        buttons.forEach(btn => btn.classList.remove("active"));

        document.getElementById(button.dataset.tab).hidden = false;
        button.classList.add("active");
    };
});

// Copy to clipboard functionality
function copyToClipboard(button) {
    button.onclick = async function () {
        const target = document.getElementById(this.dataset.copyTarget);
        await navigator.clipboard.writeText(target.value);
        const oldText = this.textContent;
        this.textContent = "✓ Copied!";
        setTimeout(() => {
            this.textContent = oldText;
        }, 1500);
    };
}

document.querySelectorAll(".copy-button").forEach(button => {
    copyToClipboard(button);
});