(function () {
  const game = window.GrokCheck;
  const root = document.getElementById("app");
  const answers = [];
  let index = 0;

  const meterMax = {
    learn: 16,
    copy: 16,
    verify: 10,
    integrity: 12,
    first: 14,
  };

  const meterLabels = {
    learn: "Learning",
    copy: "Shortcut pull",
    verify: "Checks answers",
    integrity: "Honesty",
    first: "Tries first",
  };

  function clampPercent(value, max) {
    const bounded = Math.max(0, Math.min(max, value));
    return Math.round((bounded / max) * 100);
  }

  function startScreen() {
    root.innerHTML =
      '<div class="card">' +
      "<h2>Seven choices. One recommendation.</h2>" +
      '<p class="prompt">Play this with a student. They pick what they would actually do — not the answer that sounds virtuous. At the end you get a plain recommendation: whether Grok should be a study partner, a maybe-with-rules, or a not-yet.</p>' +
      '<p class="prompt">There are no points to win. Honest answers beat impressive ones.</p>' +
      '<div class="actions"><button class="primary" id="begin">Start the game</button></div>' +
      "</div>";
    document.getElementById("begin").addEventListener("click", function () {
      index = 0;
      answers.length = 0;
      renderQuestion();
    });
  }

  function renderProgress() {
    return (
      '<div class="progress" aria-hidden="true">' +
      game.scenarios
        .map(function (_scenario, i) {
          return "<span class=\"" + (i <= index ? "on" : "") + "\"></span>";
        })
        .join("") +
      "</div>"
    );
  }

  function renderQuestion() {
    const scenario = game.scenarios[index];
    const choices = scenario.choices
      .map(function (choice) {
        return (
          '<button class="choice" data-id="' +
          choice.id +
          '">' +
          choice.label +
          "</button>"
        );
      })
      .join("");

    root.innerHTML =
      '<div class="card">' +
      renderProgress() +
      '<div class="eyebrow">Scene ' +
      (index + 1) +
      " of " +
      game.scenarios.length +
      "</div>" +
      "<h2>" +
      scenario.title +
      "</h2>" +
      '<p class="prompt">' +
      scenario.prompt +
      "</p>" +
      '<div class="choices">' +
      choices +
      "</div></div>";

    root.querySelectorAll(".choice").forEach(function (button) {
      button.addEventListener("click", function () {
        answers.push({
          scenarioId: scenario.id,
          choiceId: button.getAttribute("data-id"),
        });
        index += 1;
        if (index >= game.scenarios.length) {
          renderResult();
        } else {
          renderQuestion();
        }
      });
    });
  }

  function meterRow(key, scores) {
    const width = clampPercent(scores[key], meterMax[key]);
    return (
      '<div class="meter"><label><span>' +
      meterLabels[key] +
      "</span><span>" +
      scores[key] +
      '</span></label><div class="bar"><i style="width:' +
      width +
      '%"></i></div></div>'
    );
  }

  function renderResult() {
    const result = game.play(answers);
    const verdict = result.verdict;
    const scores = result.scores;

    root.innerHTML =
      '<div class="card">' +
      '<div class="verdict ' +
      verdict.tone +
      '">Recommendation</div>' +
      "<h2>" +
      verdict.headline +
      "</h2>" +
      '<p class="prompt">' +
      verdict.student +
      "</p>" +
      '<div class="meters">' +
      meterRow("learn", scores) +
      meterRow("copy", scores) +
      meterRow("verify", scores) +
      meterRow("integrity", scores) +
      meterRow("first", scores) +
      "</div>" +
      '<div class="note"><h3>Note for the adult</h3><p>' +
      verdict.adult +
      "</p></div>" +
      '<div class="actions">' +
      '<button class="primary" id="again">Play again</button>' +
      '<button class="ghost" id="home">Back to start</button>' +
      "</div>" +
      '<p class="fine">This is a conversation starter, not a diagnosis. If class rules forbid AI, follow those rules.</p>' +
      "</div>";

    document.getElementById("again").addEventListener("click", function () {
      index = 0;
      answers.length = 0;
      renderQuestion();
    });
    document.getElementById("home").addEventListener("click", startScreen);
  }

  startScreen();
})();
