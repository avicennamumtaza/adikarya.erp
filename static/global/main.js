/* ADIKARYA — shared scripts */

/* Scroll reveal */
const obs = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("revealed");
        obs.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.1 },
);
document.querySelectorAll(".reveal").forEach((el) => obs.observe(el));

/* Mobile nav toggle */
function toggleMobileNav() {
  document.getElementById("mobileNav").classList.toggle("open");
}

/* Highlight active nav link based on current page */
(function () {
  let path = window.location.pathname.split("/").pop();
  if (path === "" || path === "/") path = "index.html";
  document.querySelectorAll("[data-nav]").forEach((link) => {
    const href = link.getAttribute("href");
    if (href === path) link.classList.add("active");
  });
})();

/* FAQ accordion */
function toggleFaq(el) {
  const item = el.closest(".faq-item");
  const wasOpen = item.classList.contains("open");
  document
    .querySelectorAll(".faq-item.open")
    .forEach((i) => i.classList.remove("open"));
  if (!wasOpen) item.classList.add("open");
}

/* Simple contact / booking form handler (no backend — demo only) */
function handleFormSubmit(e, message) {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  const original = btn.innerHTML;
  btn.innerHTML = "✓ Terkirim!";
  btn.style.background = "var(--green)";
  setTimeout(() => {
    btn.innerHTML = original;
    btn.style.background = "";
    e.target.reset();
  }, 2500);
  return false;
}
