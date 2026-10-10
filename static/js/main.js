// Small progressive enhancements. The site works without this file because
// the server validates everything.
(function () {
  var form = document.getElementById("feedback-form");
  if (!form) {
    return;
  }

  var message = document.getElementById("message");
  var counter = document.getElementById("char-count");
  var button = document.getElementById("submit-btn");

  function updateCounter() {
    counter.textContent = message.value.length;
  }
  message.addEventListener("input", updateCounter);
  updateCounter();

  // Stop accidental double clicks from sending the form twice.
  form.addEventListener("submit", function () {
    button.disabled = true;
    button.textContent = "Submitting...";
  });
})();
