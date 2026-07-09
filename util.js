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
document.querySelectorAll(".copy-button").forEach(button => {
    button.onclick = async () => {
        const target = document.getElementById(button.dataset.copyTarget);
        await navigator.clipboard.writeText(target.value);
        const oldText = button.textContent;
        button.textContent = "✓ Copied!";
        setTimeout(() => {
            button.textContent = oldText;
        }, 1500);
    };
});