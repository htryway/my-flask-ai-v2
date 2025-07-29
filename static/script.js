document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("input");

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    sendMessage(input.value.trim());
  });
});

function sendMessage(message) {
  if (!message) return;

  addMessage("user", message);
  const input = document.getElementById("input");
  const englishLevel = document.getElementById("english-level").value;
  input.value = "";
  input.focus();

  // Add temporary "Typing..." message
  const botMsg = addMessage("bot", "Typing...");

  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: message, english_level: englishLevel }),
  })
    .then(res => res.json())
    .then(data => {
      botMsg.innerText = "Bot: ";
      typeMessage(botMsg, data.reply);
    })
    .catch(err => {
      console.error(err);
      botMsg.innerText = "Bot: Oops! Something went wrong.";
    });
}

function addMessage(sender, text) {
  const chat = document.getElementById("messages");
  const msg = document.createElement("div");
  msg.className = sender;
  msg.innerText = `${sender === "user" ? "You" : "Bot"}: ${text}`;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
  return msg; // Return the element so it can be updated
}

function typeMessage(el, text, speed = 25) {
  let index = 0;
  const fullText = text;
  el.innerText = "Bot: "; // Start with prefix

  const interval = setInterval(() => {
    el.innerText += fullText[index++];
    el.scrollIntoView({ behavior: "smooth", block: "end" });

    if (index >= fullText.length) {
      clearInterval(interval);
      speak(fullText); // Speak only after typing finishes
    }
  }, speed);
}

function speak(text) {
  const synth = window.speechSynthesis;
  const utterance = new SpeechSynthesisUtterance(text);
  synth.speak(utterance);
}
